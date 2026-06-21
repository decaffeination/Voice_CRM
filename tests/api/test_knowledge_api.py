"""知识库 API 测试（mock 向量库）。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main_server.api.knowledge_api import router as knowledge_router
from main_server.core.auth.permission import Role
from tests.conftest import auth_headers, make_test_app, token_for_user


@pytest.fixture
def knowledge_client(memory_db) -> TestClient:
    return TestClient(make_test_app(knowledge_router))


@pytest.fixture
def biz_token(memory_db) -> str:
    from main_server.core.auth.user_service import create_user
    from main_server.DB import db_session

    with db_session() as session:
        user = create_user(
            session,
            username="know_user",
            password="know1234",
            roles=[Role.SALES],
        )
        return token_for_user(user.id, "know_user", [Role.SALES])


class TestKnowledgeAPI:
    def test_stats_requires_auth(self, knowledge_client: TestClient) -> None:
        # 场景：未鉴权；输入：无 token；预期：401
        resp = knowledge_client.get("/api/knowledge/stats")
        assert resp.status_code == 401

    def test_stats_success(self, knowledge_client: TestClient, biz_token: str) -> None:
        # 场景：统计信息；输入：有效 token；预期：200
        with patch(
            "main_server.services.knowledge_service.knowledge_service.stats",
            return_value={"doc_count": 0, "chunk_count": 0},
        ):
            resp = knowledge_client.get(
                "/api/knowledge/stats",
                headers=auth_headers(biz_token),
            )
            assert resp.status_code == 200
            assert "doc_count" in resp.json()

    def test_search_empty_query(self, knowledge_client: TestClient, biz_token: str) -> None:
        # 场景：空 query；输入：query=""；预期：422
        resp = knowledge_client.post(
            "/api/knowledge/search",
            headers=auth_headers(biz_token),
            json={"query": ""},
        )
        assert resp.status_code == 422

    def test_search_success(self, knowledge_client: TestClient, biz_token: str) -> None:
        # 场景：检索成功；输入：query；预期：docs 列表
        with patch(
            "main_server.services.knowledge_service.knowledge_service.search_for_agent",
            return_value={
                "query": "测试",
                "docs": [{"content": "片段"}],
                "citations": [],
                "context": "片段",
                "rejected": False,
            },
        ):
            resp = knowledge_client.post(
                "/api/knowledge/search",
                headers=auth_headers(biz_token),
                json={"query": "测试问题"},
            )
            assert resp.status_code == 200
            assert resp.json()["docs"]

    def test_list_docs(self, knowledge_client: TestClient, biz_token: str) -> None:
        # 场景：文档列表；输入：mock list；预期：items
        with patch(
            "main_server.services.knowledge_service.knowledge_service.list_documents",
            return_value=[],
        ):
            resp = knowledge_client.get(
                "/api/knowledge/docs",
                headers=auth_headers(biz_token),
            )
            assert resp.status_code == 200
            assert resp.json()["total"] == 0

    def test_search_top_k_boundary(
        self, knowledge_client: TestClient, biz_token: str
    ) -> None:
        # 场景：top_k 超限；输入：top_k=21；预期：422
        resp = knowledge_client.post(
            "/api/knowledge/search",
            headers=auth_headers(biz_token),
            json={"query": "x", "top_k": 21},
        )
        assert resp.status_code == 422

    def test_ingest_directory_admin_only(
        self, knowledge_client: TestClient, memory_db
    ) -> None:
        # 场景：非 Admin ingest；输入：sales token；预期：403
        from main_server.core.auth.user_service import create_user
        from main_server.DB import db_session

        with db_session() as session:
            user = create_user(
                session,
                username="know_sales",
                password="know1234",
                roles=[Role.SALES],
            )
            sales_token = token_for_user(user.id, "know_sales", [Role.SALES])

        resp = knowledge_client.post(
            "/api/knowledge/ingest/directory",
            headers=auth_headers(sales_token),
        )
        assert resp.status_code == 403

    def test_ingest_directory_admin(
        self, knowledge_client: TestClient, memory_db
    ) -> None:
        # 场景：Admin ingest；输入：mock ingest；预期：200
        from main_server.core.auth.user_service import create_user
        from main_server.DB import db_session

        with db_session() as session:
            admin = create_user(
                session,
                username="know_admin",
                password="know1234",
                roles=[Role.ADMIN],
            )
            admin_token = token_for_user(admin.id, "know_admin", [Role.ADMIN])

        with patch(
            "main_server.services.knowledge_service.knowledge_service.ingest_directory",
            return_value={"files": 1, "chunks": 5},
        ):
            resp = knowledge_client.post(
                "/api/knowledge/ingest/directory",
                headers=auth_headers(admin_token),
            )
        assert resp.status_code == 200
        assert resp.json()["result"]["files"] == 1

    def test_delete_doc_non_admin_forbidden(
        self, knowledge_client: TestClient, biz_token: str
    ) -> None:
        # 场景：非 Admin 删文档；输入：sales；预期：403
        resp = knowledge_client.delete(
            "/api/knowledge/docs/doc-1",
            headers=auth_headers(biz_token),
        )
        assert resp.status_code == 403
