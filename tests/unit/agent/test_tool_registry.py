"""Tool Registry 与处理器测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.tools.handlers import handle_crm_prepare_write, handle_knowledge_search
from agent.tools.registry import ToolContext, registry
from agent.state import default_conversation_state
from main_server.core.auth.permission import Role
from main_server.DB import Base
from main_server.services.tool_result import AgentToolResult


@pytest.fixture
def memory_db(monkeypatch):
    import main_server.DB.connection as conn

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    conn._engine = engine
    conn._SessionLocal = session_factory
    import main_server.DB.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    conn._engine = None
    conn._SessionLocal = None


class TestToolRegistry:
    def test_registry_has_core_tools(self) -> None:
        names = {s["function"]["name"] for s in registry.openai_schemas()}
        for expected in (
            "crm_get_customer_profile",
            "knowledge_search",
            "crm_prepare_write",
            "email_send",
            "web_search",
        ):
            assert expected in names

    @patch("agent.tools.handlers.knowledge_tool.search_knowledge")
    def test_knowledge_search_handler(self, mock_search: MagicMock) -> None:
        mock_search.return_value = {"query": "报销", "docs": [{"content": "流程"}]}
        ctx = ToolContext(
            user_id=1,
            roles=[Role.SALES],
            conversation_state=default_conversation_state(),
            turn_count=1,
        )
        result = handle_knowledge_search({"query": "报销流程"}, ctx)
        assert result["docs"]

    def test_prepare_write_sets_pending(self, memory_db) -> None:
        ctx = ToolContext(
            user_id=1,
            roles=[Role.SALES],
            conversation_state=default_conversation_state(),
            turn_count=1,
        )
        with patch("agent.tools.crm_tool.prepare_write") as mock_prepare:
            mock_prepare.return_value = AgentToolResult(
                payload={"prepared": True, "write_type": "followup"},
                side_effects={"needs_confirm": True},
            )
            result = handle_crm_prepare_write(
                {
                    "write_type": "followup",
                    "payload": {"content": "今日签合同"},
                },
                ctx,
            )
        assert result.get("prepared") is True
        assert ctx.side_effects.get("needs_confirm") is True

    def test_execute_tool_call_parses_json_args(self) -> None:
        ctx = ToolContext(
            user_id=None,
            roles=[],
            conversation_state=default_conversation_state(),
            turn_count=1,
        )
        with patch.object(registry, "execute") as mock_exec:
            mock_exec.return_value = {"ok": True}
            registry.execute_tool_call(
                {
                    "id": "call_1",
                    "function": {
                        "name": "web_search",
                        "arguments": json.dumps({"query": "测试"}),
                    },
                },
                ctx,
            )
            mock_exec.assert_called_once()
            assert mock_exec.call_args[0][0] == "web_search"
