"""Public web search adapters used for optional profile enrichment."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientResponseError


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str
    score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
        }


class TavilySearchClient:
    """Minimal Tavily client.

    The API key must be provided through ``TAVILY_API_KEY``. Search results are
    treated as public evidence candidates and should be reviewed before being
    used for individual-level modeling.
    """

    endpoint = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "").strip()
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(self, query: str, *, max_results: int = 5) -> List[SearchResult]:
        if not self.enabled:
            raise RuntimeError("TAVILY_API_KEY is not configured")
        query = sanitize_query(query)
        if not query:
            return []

        payload = {
            "query": query,
            "search_depth": "basic",
            "max_results": max(1, min(max_results, 10)),
            "include_answer": False,
            "include_raw_content": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.endpoint, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

        return [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                content=str(item.get("content", "")),
                score=item.get("score"),
            )
            for item in data.get("results", [])
            if item.get("url")
        ]

    async def search_with_fallbacks(self, queries: List[str], *, max_results: int = 5) -> List[SearchResult]:
        """Try multiple queries and merge unique results.

        Tavily may reject some CJK-heavy queries as invalid. This method skips
        invalid queries and continues with fallback query variants.
        """
        merged: Dict[str, SearchResult] = {}
        for query in queries:
            try:
                results = await self.search(query, max_results=max_results)
            except ClientResponseError as exc:
                if exc.status == 400:
                    continue
                raise
            for result in results:
                merged.setdefault(result.url, result)
            if len(merged) >= max_results:
                break
        return list(merged.values())[:max_results]


def sanitize_query(query: str) -> str:
    """Normalize search text before sending it to Tavily."""
    query = (query or "").strip()
    query = re.sub(r"\s+", " ", query)
    query = query.replace("“", '"').replace("”", '"')
    return query[:380]
