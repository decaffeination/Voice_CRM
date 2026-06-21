"""AgentService 单元测试（mock Graph）。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from main_server.core.exceptions import PipelineError
from main_server.memory.memory_schema import ActorContext, TurnContext
from main_server.services.agent_service import agent_service


@pytest.fixture
def turn() -> TurnContext:
    actor = ActorContext(
        user_id=1,
        username="admin",
        roles=["Admin"],
        session_id="agent-svc-test",
        channel="text",
    )
    return TurnContext(actor=actor, user_input="你好")


class TestAgentService:
    def test_invoke_returns_graph_response(self, turn: TurnContext) -> None:
        # 场景：Graph 成功；输入：mock invoke；预期：text + state
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "final_response": "助手回复",
            "conversation_state": {"turn_count": 1},
            "tool_result": None,
        }
        with patch("main_server.services.agent_service.get_graph", return_value=mock_graph):
            result = agent_service.invoke(turn=turn)
        assert result.text == "助手回复"
        assert result.conversation_state["turn_count"] == 1
        mock_graph.invoke.assert_called_once()

    def test_invoke_wraps_unexpected_error(self, turn: TurnContext) -> None:
        # 场景：Graph 抛非 AppError；输入：RuntimeError；预期：PipelineError
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = RuntimeError("graph boom")
        with patch("main_server.services.agent_service.get_graph", return_value=mock_graph):
            with pytest.raises(PipelineError, match="Agent"):
                agent_service.invoke(turn=turn)
