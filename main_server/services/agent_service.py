"""Agent Graph 内部调用层（Infrastructure / Agent Adapter）。

**禁止外部直接调用** ``agent_service.invoke()``。
唯一入口为 ``main_server.services.pipeline.chat_pipeline.ChatPipeline``。

Memory 读写由 Graph 内 memory_load / memory_save 节点完成；本模块只负责
组装 initial_state 并 invoke LangGraph。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.graph import get_graph
from main_server.core.context import user_id_var
from main_server.core.exceptions import AppError, PipelineError
from main_server.memory.memory_schema import TurnContext


@dataclass
class AgentInvokeResult:
    text: str
    conversation_state: dict[str, Any]
    tool_result: Any = None
    citations: list[dict[str, Any]] | None = None


class AgentService:
    def invoke(self, *, turn: TurnContext) -> AgentInvokeResult:
        actor = turn.actor
        user_id_var.set(actor.user_id)

        graph = get_graph()
        initial_state = {
            "session_id": actor.session_id,
            "user_input": turn.user_input,
            "channel": actor.channel,
            "user_id": actor.user_id,
            "roles": list(actor.roles),
            "step_count": 0,
            "tool_results": [],
        }
        config = {"configurable": {"thread_id": actor.session_id}}
        try:
            result = graph.invoke(initial_state, config=config)
        except AppError:
            raise
        except Exception as exc:
            raise PipelineError("Agent 处理失败", stage="agent_invoke") from exc

        final_response = result.get("final_response", "")
        updated_state = result.get("conversation_state") or {}

        return AgentInvokeResult(
            text=final_response,
            conversation_state=updated_state,
            tool_result=result.get("tool_result"),
            citations=result.get("citations") or [],
        )


agent_service = AgentService()
