"""知识库生命周期：版本管理、删除、ingest 状态追踪。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main_server.api.knowledge_api import router as knowledge_router
from main_server.core.auth.jwt_auth import create_access_token
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.core.exception_handlers import register_exception_handlers
from main_server.DB import db_session
from main_server.knowledge.doc_registry import (
    build_doc_id,
    compute_file_hash,
    get_document,
    list_documents,
)
from main_server.knowledge.ingest import ingest_file
from main_server.services.knowledge_service import KnowledgeService


@pytest.fixture
def kb_client(memory_db, tmp_path, monkeypatch) -> TestClient:
    docs_dir = tmp_path / "knowledge"
    docs_dir.mkdir()
    chroma_dir = tmp_path / "chroma"
    chroma_dir.mkdir()

    from main_server.config.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings.knowledge, "docs_path", str(docs_dir))
    monkeypatch.setattr(settings.knowledge, "chroma_path", str(chroma_dir))

    with db_session() as session:
        admin = create_user(
            session,
            username="kb_admin",
            password="admin123",
            roles=[Role.ADMIN],
        )
        admin_id = admin.id
        sales = create_user(
            session,
            username="kb_sales",
            password="sales123",
            roles=[Role.SALES],
        )
        sales_id = sales.id

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(knowledge_router)
    client = TestClient(app)
    client.admin_token = create_access_token(admin_id, "kb_admin", [Role.ADMIN])
    client.sales_token = create_access_token(sales_id, "kb_sales", [Role.SALES])
    client.docs_dir = docs_dir
    return client


class TestDocRegistry:
    def test_build_doc_id_stable(self) -> None:
        assert build_doc_id("报销制度.pdf") == build_doc_id("报销制度.pdf")
        assert build_doc_id("A.txt") != build_doc_id("B.txt")

    def test_compute_file_hash(self, tmp_path: Path) -> None:
        path = tmp_path / "demo.txt"
        path.write_text("hello", encoding="utf-8")
        assert compute_file_hash(path) == compute_file_hash(path)


class TestIngestLifecycle:
    @patch("main_server.knowledge.ingest.get_vector_store")
    @patch("main_server.knowledge.ingest.invalidate_index_cache")
    def test_reingest_same_hash_is_unchanged(
        self,
        mock_invalidate: MagicMock,
        mock_store_factory: MagicMock,
        memory_db,
        tmp_path: Path,
    ) -> None:
        mock_store = MagicMock()
        mock_store.add_chunks.return_value = 2
        mock_store.delete_by_doc_id.return_value = 0
        mock_store_factory.return_value = mock_store

        path = tmp_path / "policy.txt"
        path.write_text("报销制度内容", encoding="utf-8")

        first = ingest_file(path, operator_user_id=1, logical_name="policy.txt")
        second = ingest_file(path, operator_user_id=1, logical_name="policy.txt")

        assert first["version"] == 1
        assert second["unchanged"] is True
        assert second["version"] == 1
        mock_store.add_chunks.assert_called_once()

    @patch("main_server.knowledge.ingest.get_vector_store")
    @patch("main_server.knowledge.ingest.invalidate_index_cache")
    def test_reingest_changed_content_bumps_version(
        self,
        mock_invalidate: MagicMock,
        mock_store_factory: MagicMock,
        memory_db,
        tmp_path: Path,
    ) -> None:
        mock_store = MagicMock()
        mock_store.add_chunks.return_value = 3
        mock_store.delete_by_doc_id.return_value = 2
        mock_store_factory.return_value = mock_store

        path = tmp_path / "policy.txt"
        path.write_text("版本一", encoding="utf-8")
        first = ingest_file(path, logical_name="policy.txt")
        path.write_text("版本二内容更长一些", encoding="utf-8")
        second = ingest_file(path, logical_name="policy.txt")

        assert first["version"] == 1
        assert second["version"] == 2
        assert second["replaced"] is True
        mock_store.delete_by_doc_id.assert_called_once()


class TestKnowledgeLifecycleAPI:
    @patch("main_server.services.knowledge_service.get_vector_store")
    @patch("main_server.services.knowledge_service.invalidate_index_cache")
    @patch("main_server.api.knowledge_api.knowledge_service.ingest_file")
    def test_list_and_delete_document(
        self,
        mock_ingest_file: MagicMock,
        mock_invalidate: MagicMock,
        mock_store_factory: MagicMock,
        kb_client: TestClient,
        memory_db,
    ) -> None:
        doc_id = build_doc_id("policy.txt")
        mock_ingest_file.return_value = {
            "doc_id": doc_id,
            "filename": "policy.txt",
            "version": 1,
            "chunks": 2,
            "unchanged": False,
        }

        from main_server.knowledge.doc_registry import upsert_active_document

        upsert_active_document(
            doc_id=doc_id,
            filename="policy.txt",
            file_hash="abc",
            chunk_count=2,
            file_path="/tmp/policy.txt",
            operator_user_id=1,
            version=1,
        )

        mock_store = MagicMock()
        mock_store.delete_by_doc_id.return_value = 2
        mock_store_factory.return_value = mock_store

        list_resp = kb_client.get(
            "/api/knowledge/docs",
            headers={"Authorization": f"Bearer {kb_client.sales_token}"},
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1

        delete_resp = kb_client.delete(
            f"/api/knowledge/docs/{doc_id}",
            headers={"Authorization": f"Bearer {kb_client.admin_token}"},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["removed_chunks"] == 2

        deleted = get_document(doc_id)
        assert deleted is not None
        assert deleted.status == "deleted"
        assert list_documents() == []

    def test_delete_requires_admin(self, kb_client: TestClient, memory_db) -> None:
        doc_id = build_doc_id("x.txt")
        from main_server.knowledge.doc_registry import upsert_active_document

        upsert_active_document(
            doc_id=doc_id,
            filename="x.txt",
            file_hash="abc",
            chunk_count=1,
            file_path="/tmp/x.txt",
            operator_user_id=1,
            version=1,
        )

        resp = kb_client.delete(
            f"/api/knowledge/docs/{doc_id}",
            headers={"Authorization": f"Bearer {kb_client.sales_token}"},
        )
        assert resp.status_code == 403

    @patch("main_server.services.knowledge_service.get_vector_store")
    def test_delete_service_raises_not_found(
        self,
        mock_store_factory: MagicMock,
        memory_db,
    ) -> None:
        mock_store_factory.return_value = MagicMock()
        service = KnowledgeService()
        from main_server.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            service.delete_document("missing-doc")
