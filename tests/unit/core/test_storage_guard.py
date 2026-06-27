"""存储层异常守卫测试（CRM / Knowledge / Memory）。"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock

import pytest

from main_server.CRM.storage_guard import crm_db_session, guard_crm
from main_server.knowledge.storage_guard import guard_knowledge
from main_server.core.exceptions import (
    AppError,
    CRMError,
    KnowledgeError,
    MemoryError,
    ValidationError,
)
from main_server.memory import memory_manager as memory_manager_module


class TestGuardCrm:
    def test_passes_through_app_error(self) -> None:
        with pytest.raises(ValidationError):
            guard_crm("查询客户", lambda: (_ for _ in ()).throw(ValidationError("x")))

    def test_wraps_generic_exception(self) -> None:
        with pytest.raises(CRMError) as exc_info:
            guard_crm("查询客户", lambda: (_ for _ in ()).throw(RuntimeError("db")))
        err = exc_info.value
        assert err.code == "STORAGE_ERROR"
        assert err.status_code == 500
        assert "查询客户失败" in err.message


class TestCrmDbSession:
    def test_wraps_db_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        @contextmanager
        def fake_db_session() -> Generator[MagicMock, None, None]:
            raise RuntimeError("connection lost")
            yield MagicMock()

        monkeypatch.setattr(
            "main_server.CRM.storage_guard.db_session",
            fake_db_session,
        )
        with pytest.raises(CRMError) as exc_info:
            with crm_db_session():
                pass
        assert exc_info.value.code == "STORAGE_ERROR"
        assert exc_info.value.message == "数据库操作失败"

    def test_passes_through_app_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        @contextmanager
        def fake_db_session() -> Generator[MagicMock, None, None]:
            raise CRMError("业务错误")
            yield MagicMock()

        monkeypatch.setattr(
            "main_server.CRM.storage_guard.db_session",
            fake_db_session,
        )
        with pytest.raises(CRMError) as exc_info:
            with crm_db_session():
                pass
        assert exc_info.value.message == "业务错误"


class TestGuardKnowledge:
    def test_wraps_generic_exception(self) -> None:
        with pytest.raises(KnowledgeError) as exc_info:
            guard_knowledge("检索向量库", lambda: (_ for _ in ()).throw(OSError("io")))
        err = exc_info.value
        assert err.code == "STORAGE_ERROR"
        assert "检索向量库失败" in err.message

    def test_passes_through_app_error(self) -> None:
        with pytest.raises(KnowledgeError):
            guard_knowledge(
                "写入",
                lambda: (_ for _ in ()).throw(
                    KnowledgeError("已有错误", code="NOT_FOUND", status_code=404)
                ),
            )


class TestGuardMemory:
    def test_load_history_wraps_db_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(_session_id: str) -> None:
            raise RuntimeError("sqlite error")

        monkeypatch.setattr(
            memory_manager_module.history_memory,
            "load_active",
            boom,
        )
        manager = memory_manager_module.MemoryManager()
        with pytest.raises(MemoryError) as exc_info:
            manager.load_history("sess-1")
        assert "加载对话历史失败" in exc_info.value.message
        assert exc_info.value.code == "MEMORY_ERROR"

    def test_load_history_passes_app_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def raise_validation(_session_id: str) -> None:
            raise ValidationError("会话无效")

        monkeypatch.setattr(
            memory_manager_module.history_memory,
            "load_active",
            raise_validation,
        )
        manager = memory_manager_module.MemoryManager()
        with pytest.raises(ValidationError):
            manager.load_history("sess-1")
