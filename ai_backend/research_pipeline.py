
import re

from .agents import (
    build_search_agent,
    writer_chain,
    critic_chain,
)
from .tools import scrape_url


def run_research_pipeline(topic: str) -> dict:
    """
    Research workflow:
    1. Search the web.
    2. Scrape a relevant webpage.
    3. Write a report.
    4. Review the report.
    """

    topic = (topic or "").strip()

    if not topic:
        raise ValueError("Research topic cannot be empty.")

    state = {
        "topic": topic,
        "search_results": "",
        "scraped_content": "",
        "report": "",
        "feedback": "",
    }

    # Stage 1: Search the web
    print("[1/4] Searching the web...", flush=True)

    search_agent = build_search_agent()

    search_result = search_agent.invoke({
        "messages": [{
            "role": "user",
            "content": (
                f"Search for reliable sources about: {topic}. "
                "Return titles, URLs, and key findings."
            ),
        }]
    })

    state["search_results"] = (
        search_result["messages"][-1].content
    )

    # Stage 2: Scrape a relevant webpage directly
    print("[2/4] Reading a source webpage...", flush=True)

    urls = re.findall(
        r'https?://[^\s<>"\'\]\)]+',
        state["search_results"],
    )

    urls = list(dict.fromkeys(
        url.rstrip(".,;:!?") for url in urls
    ))

    for url in urls[:3]:
        print(f"Trying source: {url}", flush=True)

        page_content = scrape_url.invoke({"url": url})

        if (
            page_content
            and len(page_content) > 100
            and not page_content.startswith((
                "Could not scrape URL:",
                "Scraping failed:",
                "Private or non-public URLs are not allowed.",
                "Local URLs are not allowed.",
                "Invalid URL.",
                "Could not resolve the website hostname.",
            ))
            and "No readable content found" not in page_content
        ):
            state["scraped_content"] = (
                f"Source URL: {url}\n\n{page_content[:4000]}"
            )
            break

    if not state["scraped_content"]:
        state["scraped_content"] = (
            "No webpage could be scraped successfully. "
            "Use the search results cautiously and disclose this limitation."
        )

    # Stage 3: Generate the report using a smaller prompt
    print("[3/4] Writing the research report...", flush=True)

    research_material = (
        "SEARCH RESULTS:\n"
        + state["search_results"][:2500]
        + "\n\nWEBPAGE CONTENT:\n"
        + state["scraped_content"][:4000]
    )

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_material,
    })

    # Stage 4: Review the report
    print("[4/4] Reviewing the report...", flush=True)

    state["feedback"] = critic_chain.invoke({
        "report": state["report"][:4000],
    })

    print("Research pipeline completed.", flush=True)

    return state
