"""Agent 知识库工具封装 → main_server.services.knowledge_service。"""

from __future__ import annotations

from typing import Any

from main_server.services.knowledge_service import knowledge_service


def search_knowledge(query: str, top_k: int | None = None) -> dict[str, Any]:
    return knowledge_service.search_for_agent(query, top_k=top_k)
