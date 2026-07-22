"""tavily web search. mock mode: canned fake results, no api call."""
import os
from agent.config import MOCK_MODE

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web for current info not in the knowledge base (recent studies, product facts etc).",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


def _mock_search(query, k=3):
    return [
        {"title": f"Mock result {i+1} for '{query}'", "url": f"https://example.com/{i+1}", "snippet": "mock snippet, no real web call made."}
        for i in range(k)
    ]


def _real_search(query, k=3):
    import requests
    resp = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": os.getenv("TAVILY_API_KEY"), "query": query, "max_results": k},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return [{"title": r["title"], "url": r["url"], "snippet": r["content"]} for r in data.get("results", [])]


def search_web(query: str, k: int = 3):
    return _mock_search(query, k) if MOCK_MODE else _real_search(query, k)
