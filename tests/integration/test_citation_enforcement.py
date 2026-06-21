"""Citation 强制、LLM 委托、会话级联删除集成测试。"""

from __future__ import annotations

import uuid
from unittest.mock import patch

from agent.nodes.response_node import (
    _append_citation_footer,
    _collect_knowledge_citations,
    _enforce_citations,
    _has_required_citations,
)
from main_server.memory import history_memory
from main_server.services.llm_service import LLMService


class TestLLMService:
    def test_delegates_to_provider(self) -> None:
        # 场景：LLM 委托 Provider；输入：mock provider；预期：返回 ok
        service = LLMService()
        with patch.object(service, "_provider") as mock_provider:
            mock_provider.return_value.chat.return_value = "ok"
            assert service.chat([{"role": "user", "content": "hi"}]) == "ok"


class TestCitationEnforcement:
    def test_collect_citations_from_tool_results(self) -> None:
        citations = [{"index": 1, "ref": "[1]", "source": "a.txt"}]
        found = _collect_knowledge_citations(
            [{"tool": "knowledge_search", "citations": citations}]
        )
        assert len(found) == 1

    def test_has_required_citations(self) -> None:
        citations = [{"index": 1, "ref": "[1]"}]
        assert _has_required_citations("根据制度说明[1]", citations)
        assert not _has_required_citations("没有引用", citations)

    def test_append_footer(self) -> None:
        text = _append_citation_footer(
            "回答正文",
            [{"ref": "[1]", "source": "test.txt", "page": 2}],
        )
        assert "参考来源" in text
        assert "[1]" in text

    def test_enforce_retries_then_footer(self) -> None:
        citations = [{"index": 1, "ref": "[1]", "source": "x"}]
        messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
        with patch("agent.nodes.response_node.llm_service") as mock_llm:
            mock_llm.chat.return_value = "仍无引用"
            result = _enforce_citations("仍无引用", citations, messages)
        assert "参考来源" in result


class TestSessionDeleteCascade:
    def test_delete_session_data(self, memory_db) -> None:
        # 场景：删除会话级联 Memory；输入：history/state/summary；预期：全部清除
        from main_server.memory.memory_manager import memory_manager

        session_id = "sess-delete-test"
        memory_manager.save_history(
            session_id,
            [{"role": "user", "content": "hi", "channel": "text"}],
        )
        memory_manager.save_state(session_id, {"turn_count": 1})
        memory_manager.save_summary(session_id, "摘要")

        deleted = memory_manager.delete_session_data(session_id)
        assert deleted["messages"] >= 1
        assert deleted["state"] == 1
        assert deleted["summary"] == 1
        assert history_memory.count(session_id) == 0
