
import os
import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    raise ValueError(
        "TAVILY_API_KEY is missing. Add it to your .env file."
    )

tavily = TavilyClient(api_key=TAVILY_API_KEY)


@tool
def web_search(query: str) -> str:
    """Search the web for recent information and return titles, URLs, and snippets."""
    try:
        results = tavily.search(query=query, max_results=5)
        output = []

        for result in results.get("results", []):
            output.append(
                f"Title: {result.get('title', 'No title')}\n"
                f"URL: {result.get('url', 'No URL')}\n"
                f"Snippet: {result.get('content', '')[:500]}"
            )

        return (
            "\n\n--------------------\n\n".join(output)
            if output
            else "No search results found."
        )

    except Exception as exc:
        return f"Web search failed: {exc}"


@tool
def scrape_url(url: str) -> str:
    """Fetch a public HTTP or HTTPS webpage and return its readable text."""
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return "Invalid URL. Use a public HTTP or HTTPS webpage."

        # Reject local and private destinations.
        hostname = parsed.hostname
        if hostname.lower() == "localhost" or hostname.lower().endswith(".localhost"):
            return "Local URLs are not allowed."

        try:
            addresses = socket.getaddrinfo(
                hostname, None, type=socket.SOCK_STREAM
            )
            for address in addresses:
                ip = ipaddress.ip_address(address[4][0])
                if not ip.is_global:
                    return "Private or non-public URLs are not allowed."
        except socket.gaierror:
            return "Could not resolve the website hostname."

        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
            allow_redirects=False,
        )
        response.raise_for_status()

        if "text/html" not in response.headers.get("Content-Type", "").lower():
            return "The URL did not return an HTML webpage."

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "form"]
        ):
            tag.decompose()

        page_text = soup.get_text(separator=" ", strip=True)

        if not page_text:
            return "No readable content found on this page."

        return page_text[:8000]

    except requests.exceptions.RequestException as exc:
        return f"Could not scrape URL: {exc}"
    except Exception as exc:
        return f"Scraping failed: {exc}"
