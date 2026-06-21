"""Agent 搜索工具封装 → main_server.services.search_service。"""

from __future__ import annotations

from typing import Any

from main_server.services.search_service import search_service


def web_search(query: str, *, max_results: int | None = None) -> dict[str, Any]:
    return search_service.web_search(query, max_results=max_results)


def search_company_contact(company_name: str) -> dict[str, Any]:
    return search_service.search_company_contact(company_name)
