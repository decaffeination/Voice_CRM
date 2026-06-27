from __future__ import annotations

import httpx

from main_server.config.settings import get_settings
from main_server.core.logger import logger
from main_server.core.provider_retry import call_with_retry


class TavilySearchProvider:
    """Tavily Search API。"""

    _API_URL = "https://api.tavily.com/search"

    def search(self, query: str, *, max_results: int | None = None) -> dict:
        settings = get_settings().tools.web_search
        if not settings.enabled:
            return {"query": query, "results": [], "error": "web_search_disabled"}

        api_key = settings.tavily_api_key.strip()
        if not api_key:
            return {"query": query, "results": [], "error": "tavily_api_key_missing"}

        limit = max_results or settings.max_results
        keyword = query.strip()
        if not keyword:
            return {"query": query, "results": [], "error": "empty_query"}

        payload = {
            "api_key": api_key,
            "query": keyword,
            "max_results": limit,
            "search_depth": "basic",
            "include_answer": False,
        }

        def _fetch() -> list[dict]:
            with httpx.Client(timeout=settings.timeout_seconds) as client:
                response = client.post(self._API_URL, json=payload)
                response.raise_for_status()
            data = response.json()
            results: list[dict] = []
            for item in data.get("results") or []:
                results.append(
                    {
                        "title": item.get("title") or "",
                        "url": item.get("url") or "",
                        "snippet": item.get("content") or "",
                    }
                )
            return results[:limit]

        try:
            results = call_with_retry(
                _fetch,
                provider="tavily",
                retryable=(httpx.HTTPError,),
                thread_timeout=True,
            )
        except Exception as exc:
            logger.warning("tavily_search.failed query=%s error=%s", keyword, exc)
            return {"query": keyword, "results": [], "error": str(exc)}

        logger.info("tavily_search query=%s hit_count=%s", keyword, len(results))
        return {"query": keyword, "results": results, "provider": "tavily"}

    def search_company_contact(self, company_name: str) -> dict:
        import re

        name = company_name.strip()
        search = self.search(f"{name} 官网 联系邮箱 电话")
        emails: list[str] = []
        phones: list[str] = []
        for item in search.get("results") or []:
            snippet = item.get("snippet", "")
            emails.extend(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", snippet))
            phones.extend(re.findall(r"1[3-9]\d{9}", snippet))
        return {
            "company_name": name,
            "search": search,
            "emails_found": list(dict.fromkeys(emails))[:5],
            "phones_found": list(dict.fromkeys(phones))[:5],
        }
