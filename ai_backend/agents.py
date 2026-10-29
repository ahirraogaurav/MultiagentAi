
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .tools import web_search, scrape_url


# --------------------------------------------------
# 1. Load environment variables
# --------------------------------------------------

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing. Add it to your .env file."
    )


# --------------------------------------------------
# 2. Initialize the Groq language model
# --------------------------------------------------

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=GROQ_API_KEY,
)


# --------------------------------------------------
# 3. Search Agent
# --------------------------------------------------

def build_search_agent():
    """Create an agent that searches the web for research."""

    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt=(
            "You are a web research agent for a MultiAgent AI system. "
            "Search for reliable and relevant information about the "
            "user's question. Use the web_search tool. "
            "Return source titles, URLs, and key findings. "
            "Prioritize trustworthy and relevant sources. "
            "Never invent search results, facts, or source URLs. "
            "Keep your output concise to control token usage."
        ),
    )


# --------------------------------------------------
# 4. Reader Agent
# --------------------------------------------------

def build_reader_agent():
    """Create an agent that reads and summarizes web pages."""

    return create_agent(
        model=llm,
        tools=[scrape_url],
        system_prompt=(
            "You are a research reading agent. "
            "Review the search results provided by the user or "
            "the previous agent. Select a relevant URL and use "
            "the scrape_url tool to read its content. "
            "Summarize the important facts, evidence, and findings. "
            "Clearly identify uncertainty and missing information. "
            "Never claim that a webpage was read if scraping failed. "
            "Never invent facts or citations. "
            "Keep your output concise and relevant."
        ),
    )


# --------------------------------------------------
# 5. Research Report Writer
# --------------------------------------------------

writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the professional research writer for a MultiAgent AI assistant.

Your job is to produce accurate, readable, well-organized answers
based on the supplied research material.

FIRST, choose the format that best fits the user's request:

- Simple question: give a direct answer and brief explanation.
- Comparison: use a table when it improves clarity.
- Research request: create a structured research report.
- Programming question: provide code blocks and step-by-step instructions.
- Educational question: explain concepts simply with examples.
- Procedure: provide numbered steps.
- Advantages and disadvantages: use clear bullet points.

For research reports, use relevant sections from this structure:

# Descriptive Title

## Executive Summary
Summarize the most important findings in a few sentences.

## Introduction
Explain the topic and its importance.

## Key Findings
Present the main findings using headings, bullet points, or tables.

## Detailed Analysis
Explain evidence, applications, examples, and implications.

## Benefits and Applications
Describe relevant practical uses and benefits.

## Challenges and Limitations
Explain risks, uncertainty, missing evidence, and constraints.

## Future Scope
Discuss future possibilities when supported by the research material.

## Conclusion
Summarize the main takeaways.

## References
Include source titles and URLs provided in the research material.

IMPORTANT RULES:

1. Answer the user's actual question first.
2. Do not force every response into a long report.
3. Use Markdown consistently for headings, bold text, lists, tables,
   links, and code blocks.
4. Keep paragraphs short and readable.
5. Use tables only when they are useful.
6. Explain technical terms when necessary.
7. Never invent facts, statistics, citations, or URLs.
8. Do not present unsupported claims as established facts.
9. Clearly disclose when evidence is insufficient.
10. Include only relevant sections; omit unnecessary headings.
11. Preserve important qualifications and limitations in the sources.
12. Do not claim independent verification unless supported by evidence.
"""
    ),
    (
        "human",
        """User's question or research topic:
{topic}

Available research material:
{research}

Write the best-formatted answer for this request."""
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# --------------------------------------------------
# 6. Critic / Review Agent
# --------------------------------------------------

critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the quality-review agent for a MultiAgent AI research system.

Review the supplied report for:

1. Accuracy and unsupported claims.
2. Relevance to the original topic.
3. Clarity, grammar, and organization.
4. Missing evidence or important information.
5. Source quality and citation completeness.
6. Contradictions and unclear statements.
7. Whether uncertainty and limitations are disclosed.

Return a concise review containing:

## Overall Assessment
Briefly assess the report's quality.

## Strengths
List what the report does well.

## Issues to Address
Identify unsupported claims, missing evidence, or unclear sections.

## Recommendations
Suggest specific improvements.

IMPORTANT:
- Do not invent new facts or sources.
- Do not claim independent fact-checking without evidence.
- Do not treat a polished writing style as proof of accuracy.
- Focus on actionable feedback.
"""
    ),
    (
        "human",
        """Review the following research report:

{report}
"""
    ),
])

critic_chain = critic_prompt | llm | StrOutputParser()
