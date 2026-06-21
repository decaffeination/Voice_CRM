from __future__ import annotations

import re
from html import unescape
from urllib.parse import quote_plus

import httpx

from main_server.config.settings import get_settings
from main_server.core.logger import logger
from main_server.core.provider_retry import call_with_retry


class WebSearchProvider:
    """DuckDuckGo HTML 搜索（无需 API Key）。"""

    def search(self, query: str, *, max_results: int | None = None) -> dict:
        settings = get_settings().tools.web_search
        if not settings.enabled:
            return {"query": query, "results": [], "error": "web_search_disabled"}

        limit = max_results or settings.max_results
        keyword = query.strip()
        if not keyword:
            return {"query": query, "results": [], "error": "empty_query"}

        def _fetch() -> list[dict]:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(keyword)}"
            headers = {"User-Agent": "Voice-CRM/1.0"}
            with httpx.Client(timeout=settings.timeout_seconds, headers=headers) as client:
                response = client.get(url)
                response.raise_for_status()
            return _parse_ddg_html(response.text, limit)

        try:
            results = call_with_retry(
                _fetch,
                provider="web_search",
                retryable=(httpx.HTTPError,),
                thread_timeout=True,
            )
        except Exception as exc:
            logger.warning("web_search.failed query=%s error=%s", keyword, exc)
            return {"query": keyword, "results": [], "error": str(exc)}

        logger.info("web_search query=%s hit_count=%s", keyword, len(results))
        return {"query": keyword, "results": results}

    def search_company_contact(self, company_name: str) -> dict:
        """搜索公司官网/联系邮箱线索。"""
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


def _parse_ddg_html(html: str, limit: int) -> list[dict]:
    results: list[dict] = []
    blocks = re.split(r'class="result\s', html)
    for block in blocks[1:]:
        title_m = re.search(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block, re.S)
        snippet_m = re.search(r'class="result__snippet"[^>]*>(.*?)</', block, re.S)
        if not title_m:
            continue
        title = unescape(re.sub(r"<[^>]+>", "", title_m.group(2))).strip()
        url = unescape(title_m.group(1).strip())
        snippet = ""
        if snippet_m:
            snippet = unescape(re.sub(r"<[^>]+>", "", snippet_m.group(1))).strip()
        results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= limit:
            break
    return results


_web_search_provider: WebSearchProvider | None = None


def get_web_search_provider() -> WebSearchProvider:
    global _web_search_provider
    if _web_search_provider is None:
        _web_search_provider = WebSearchProvider()
    return _web_search_provider
