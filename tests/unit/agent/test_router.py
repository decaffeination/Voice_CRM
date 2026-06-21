"""Agent 路由节点单元测试。"""

from __future__ import annotations

from agent.router import (
    pending_gate_node,
    route_after_agent,
    route_after_pending_gate,
    route_after_tools,
)
from main_server.config.constants import PENDING_WRITE_AWAITING, PENDING_WRITE_DRAFT


class TestPendingGate:
    def test_confirm_keyword_routes_to_confirm(self) -> None:
        # 场景：待确认时用户说确认；输入：确认；预期：intent=confirm
        state = {
            "user_input": "确认写入",
            "conversation_state": {
                "pending_write": {"status": PENDING_WRITE_AWAITING, "type": "customer"},
            },
        }
        result = pending_gate_node(state)
        assert result["intent"] == "confirm"
        assert route_after_pending_gate({**state, **result}) == "confirm"

    def test_cancel_keyword_routes_to_cancel(self) -> None:
        # 场景：待确认时用户取消；输入：取消；预期：intent=cancel
        state = {
            "user_input": "算了取消",
            "conversation_state": {
                "pending_write": {"status": PENDING_WRITE_AWAITING},
            },
        }
        result = pending_gate_node(state)
        assert result["intent"] == "cancel"

    def test_pending_reminder_on_other_input(self) -> None:
        # 场景：待确认时无关输入；输入：随便说；预期：pending_reminder → response
        state = {
            "user_input": "今天天气怎么样",
            "conversation_state": {
                "pending_write": {"status": PENDING_WRITE_AWAITING},
            },
        }
        result = pending_gate_node(state)
        assert result["intent"] == "pending_reminder"
        assert route_after_pending_gate({**state, **result}) == "response"

    def test_no_pending_goes_to_agent(self) -> None:
        # 场景：无 pending；输入：普通问题；预期：intent=agent
        result = pending_gate_node(
            {"user_input": "查客户", "conversation_state": {}}
        )
        assert result["intent"] == "agent"
        assert route_after_pending_gate(result) == "agent"


class TestRouteAfterAgent:
    def test_tool_calls_go_to_tools(self) -> None:
        # 场景：有 tool_calls；预期：tools
        state = {"tool_calls": [{"id": "1", "function": {"name": "x"}}]}
        assert route_after_agent(state) == "tools"

    def test_draft_pending_goes_to_confirm(self) -> None:
        # 场景：draft pending；预期：confirm
        state = {
            "conversation_state": {
                "pending_write": {"status": PENDING_WRITE_DRAFT},
            },
        }
        assert route_after_agent(state) == "confirm"

    def test_default_goes_to_response(self) -> None:
        # 场景：无工具无 draft；预期：response
        assert route_after_agent({"conversation_state": {}}) == "response"


class TestRouteAfterTools:
    def test_max_steps_goes_to_response(self) -> None:
        # 场景：步数达上限；预期：response
        from main_server.config.settings import get_settings

        max_steps = get_settings().tools.agent.max_steps
        state = {"step_count": max_steps}
        assert route_after_tools(state) == "response"

    def test_under_max_returns_agent(self) -> None:
        # 场景：未达上限；预期：agent
        assert route_after_tools({"step_count": 0}) == "agent"
