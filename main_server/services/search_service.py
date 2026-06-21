from __future__ import annotations

from typing import Any

from main_server.providers.Tools.web_search import get_web_search_provider


class SearchService:
    """联网搜索业务层。"""

    def web_search(
        self, query: str, *, max_results: int | None = None
    ) -> dict[str, Any]:
        return get_web_search_provider().search(query, max_results=max_results)

    def search_company_contact(self, company_name: str) -> dict[str, Any]:
        return get_web_search_provider().search_company_contact(company_name)


search_service = SearchService()
