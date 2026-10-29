
import json
import os
import re

from django.conf import settings
from langchain_groq import ChatGroq

from ai_backend.research_pipeline import run_research_pipeline


AGENTS = {
    "research": {
        "name": "Research Assistant",
        "description": "Searches the web and generates reviewed research reports",
        "system": (
            "You are a research assistant. For research requests, gather "
            "reliable evidence, explain key findings, and acknowledge limitations."
        ),
    },
    "researcher": {
        "name": "Researcher",
        "description": "Gathers facts, background and trade-offs",
        "system": (
            "You are a careful research analyst. Present relevant facts, context, "
            "options and trade-offs. Flag uncertainty and be concise."
        ),
    },
    "coder": {
        "name": "Coder",
        "description": "Writes and reviews code",
        "system": (
            "You are a senior software engineer. Write correct, idiomatic code "
            "with explanations and edge cases. Use fenced code blocks when useful."
        ),
    },
    "writer": {
        "name": "Writer",
        "description": "Drafts clear, well-structured prose",
        "system": (
            "You are an expert writer. Produce clear, well-organized prose "
            "appropriate for the audience. Avoid filler."
        ),
    },
    "critic": {
        "name": "Critic",
        "description": "Finds flaws and risks",
        "system": (
            "You are a rigorous reviewer. Identify errors, gaps, risks and "
            "weak assumptions, and suggest concrete fixes."
        ),
    },
}

STYLES = {
    "normal": "",
    "concise": "Respond concisely and directly. Skip unnecessary preamble.",
    "explanatory": "Explain step by step and teach as you go.",
    "formal": "Use a formal, professional tone.",
}

DEFAULT_SYSTEM = (
    "You are a helpful, honest assistant. Use clear Markdown, natural paragraphs, "
    "and bullets when useful. Avoid tables unless they materially improve clarity."
)

SYNTH_SYSTEM = (
    "You are the lead assistant. Combine specialist notes into one coherent, "
    "accurate final answer in Markdown. Resolve contradictions and remove redundancy."
)


def get_llm():
    """Create the Groq chat model."""
    api_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to your .env file and load it in settings.py."
        )

    model = (
        getattr(settings, "GROQ_MODEL", None)
        or os.getenv("GROQ_MODEL")
        or "openai/gpt-oss-120b"
    )

    return ChatGroq(
        model=model,
        api_key=api_key,
        temperature=0.2,
        streaming=True,
    )


def _normalise_history(history):
    """Keep valid user/assistant messages and avoid sending excessive history."""
    messages = []

    for item in history or []:
        role = item.get("role")
        content = item.get("content", "")

        if role not in ("user", "assistant") or not content:
            continue

        messages.append({
            "role": role,
            "content": str(content),
        })

    # Keep the latest messages to reduce token usage.
    return messages[-12:]


def _langchain_messages(history, system):
    messages = [("system", system)]

    for item in history:
        messages.append((item["role"], item["content"]))

    return messages


def _complete(llm, system, history, max_chars=12000):
    """Get a complete response for routing or specialist work."""
    messages = _langchain_messages(history, system)

    # Bound the total conversation sent for this request.
    bounded = []
    remaining = max_chars

    for role, content in reversed(messages[1:]):
        content = str(content)

        if remaining <= 0:
            break

        content = content[-remaining:]
        bounded.append((role, content))
        remaining -= len(content)

    bounded.reverse()
    bounded.insert(0, ("system", system))

    result = llm.invoke(bounded)
    content = result.content

    if isinstance(content, str):
        return content

    return str(content)


def _stream(llm, system, history):
    """Stream response text in small chunks."""
    messages = _langchain_messages(history, system)

    for chunk in llm.stream(messages):
        content = chunk.content

        if isinstance(content, str) and content:
            yield content


def router_system(enabled):
    available = "\n".join(
        f"- {key}: {AGENTS[key]['description']}"
        for key in enabled
        if key in AGENTS
    )

    return (
        "You are an orchestrator. Choose which specialist agents should work "
        "on the latest user request.\n"
        f"Available agents:\n{available}\n"
        'Reply with ONLY a JSON array of agent IDs, such as ["researcher","writer"]. '
        "Choose [] for simple conversation. Choose at most 3 agents."
    )


def route(llm, history, enabled):
    if not enabled:
        return []

    try:
        raw = _complete(
            llm,
            router_system(enabled),
            history[-6:],
            max_chars=5000,
        )

        match = re.search(r"\[[\s\S]*?\]", raw)

        if not match:
            return []

        picks = json.loads(match.group(0))

        if not isinstance(picks, list):
            return []

        return [
            key for key in picks
            if isinstance(key, str) and key in enabled
        ][:3]

    except (ValueError, TypeError, json.JSONDecodeError):
        return []


def run(history, mode="auto", extra="", enabled=None):
    """
    Yield events compatible with the Django streaming frontend:
    step, delta, and error.

    mode:
      auto       -> orchestrator selects specialists
      direct     -> normal Groq assistant
      research   -> Tavily research pipeline and report generation
      researcher -> research-style response using Groq
      coder      -> coding specialist
      writer     -> writing specialist
      critic     -> review specialist
    """
    history = _normalise_history(history)

    if not history:
        yield {
            "type": "error",
            "message": "No valid conversation messages were provided.",
        }
        return

    latest_user_message = next(
        (
            item["content"]
            for item in reversed(history)
            if item["role"] == "user"
        ),
        "",
    )

    if not latest_user_message:
        yield {
            "type": "error",
            "message": "Please send a user message.",
        }
        return

    # Research pipeline has its own Groq/Tavily agents.
    if mode == "research":
        yield {
            "type": "step",
            "agent": "research",
            "name": "Research Assistant",
            "state": "working",
        }

        try:
            result = run_research_pipeline(latest_user_message)

            report = str(result.get("report", "")).strip()
            feedback = str(result.get("feedback", "")).strip()

            if not report:
                yield {
                    "type": "error",
                    "message": "The research pipeline did not generate a report.",
                }
                return

            yield {
                "type": "delta",
                "text": report,
            }

            if feedback:
                yield {
                    "type": "step",
                    "agent": "critic",
                    "name": "Review completed",
                    "state": "done",
                    "detail": "The report was reviewed.",
                }

            yield {
                "type": "step",
                "agent": "research",
                "name": "Research Assistant",
                "state": "done",
            }

        except Exception as exc:
            yield {
                "type": "error",
                "message": f"Research failed: {exc}",
            }

        yield {"type": "done"}
        return

    try:
        llm = get_llm()

        enabled_agents = [
            key for key in AGENTS
            if key != "research" and (enabled is None or key in enabled)
        ]

        system = DEFAULT_SYSTEM
        if extra:
            system += "\n\nAdditional instructions:\n" + str(extra)

        # A selected specialist mode.
        if mode in AGENTS and mode != "research":
            specialist_system = AGENTS[mode]["system"]

            if extra:
                specialist_system += "\n\nAdditional instructions:\n" + str(extra)

            yield {
                "type": "step",
                "agent": mode,
                "name": AGENTS[mode]["name"],
                "state": "working",
            }

            for text in _stream(llm, specialist_system, history):
                yield {"type": "delta", "text": text}

            yield {
                "type": "step",
                "agent": mode,
                "name": AGENTS[mode]["name"],
                "state": "done",
            }
            yield {"type": "done"}
            return

        # Direct chat skips specialist routing.
        if mode == "direct":
            for text in _stream(llm, system, history):
                yield {"type": "delta", "text": text}

            yield {"type": "done"}
            return

        # Automatic multi-agent mode.
        yield {
            "type": "step",
            "agent": "orchestrator",
            "name": "Orchestrator",
            "state": "working",
        }

        picks = route(llm, history, enabled_agents)

        yield {
            "type": "step",
            "agent": "orchestrator",
            "name": "Orchestrator",
            "state": "done",
            "detail": (
                ", ".join(AGENTS[key]["name"] for key in picks)
                if picks else "answering directly"
            ),
        }

        if not picks:
            for text in _stream(llm, system, history):
                yield {"type": "delta", "text": text}

            yield {"type": "done"}
            return

        notes = []

        for key in picks:
            agent = AGENTS[key]

            yield {
                "type": "step",
                "agent": key,
                "name": agent["name"],
                "state": "working",
            }

            specialist_system = agent["system"]

            if extra:
                specialist_system += "\n\nAdditional instructions:\n" + str(extra)

            output = _complete(
                llm,
                specialist_system,
                history,
                max_chars=12000,
            )

            notes.append(f"### {agent['name']}\n{output}")

            yield {
                "type": "step",
                "agent": key,
                "name": agent["name"],
                "state": "done",
            }

        yield {
            "type": "step",
            "agent": "synth",
            "name": "Final answer",
            "state": "working",
        }

        synth_history = history[:-1] + [{
            "role": "user",
            "content": (
                f"{latest_user_message}\n\n"
                "Specialist notes:\n\n"
                + "\n\n".join(notes)
            ),
        }]

        for text in _stream(llm, SYNTH_SYSTEM, synth_history):
            yield {"type": "delta", "text": text}

        yield {
            "type": "step",
            "agent": "synth",
            "name": "Final answer",
            "state": "done",
        }
        yield {"type": "done"}

    except Exception as exc:
        yield {
            "type": "error",
            "message": str(exc),
        }
