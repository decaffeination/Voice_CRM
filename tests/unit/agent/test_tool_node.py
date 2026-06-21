"""tool_node 单元测试。"""

from __future__ import annotations

from unittest.mock import patch

from agent.nodes.tool_node import tool_node


class TestToolNode:
    def test_executes_tool_and_appends_messages(self) -> None:
        # 场景：执行工具；输入：tool_calls；预期：tool 消息 + tool_results
        mock_result = {"tool": "web_search", "results": []}
        with patch("agent.tools.registry.registry.execute_tool_call") as mock_exec:
            mock_exec.return_value = mock_result
            out = tool_node(
                {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "web_search",
                                "arguments": '{"query": "测试"}',
                            },
                        }
                    ],
                    "conversation_state": {"turn_count": 1},
                    "user_id": 1,
                    "roles": ["Sales"],
                    "channel": "text",
                }
            )

        assert out["tool_calls"] is None
        assert out["tool_result"] == mock_result
        assert len(out["agent_messages"]) == 1
        assert out["agent_messages"][0]["role"] == "tool"
        mock_exec.assert_called_once()

    def test_needs_confirm_from_side_effects(self) -> None:
        # 场景：side_effects needs_confirm；预期：needs_confirm=True
        with patch("agent.tools.registry.registry.execute_tool_call") as mock_exec:
            def _side_effect(tool_call, ctx):
                ctx.side_effects["needs_confirm"] = True
                return {"prepared": True, "write_type": "customer"}

            mock_exec.side_effect = _side_effect
            out = tool_node(
                {
                    "tool_calls": [
                        {
                            "id": "c1",
                            "function": {"name": "crm_prepare_write", "arguments": "{}"},
                        }
                    ],
                    "conversation_state": {},
                }
            )
        assert out["needs_confirm"]
