from __future__ import annotations

from functools import lru_cache

import agent.tools.handlers  # noqa: F401 — 注册 Tool Registry
from agent.checkpointer import CHECKPOINTER_ENABLED, get_checkpointer
from agent.nodes.agent_node import agent_node
from agent.nodes.confirm_node import confirm_node
from agent.nodes.memory_node import memory_load_node, memory_save_node
from agent.nodes.response_node import response_node
from agent.nodes.tool_node import tool_node
from agent.router import (
    pending_gate_node,
    route_after_agent,
    route_after_pending_gate,
    route_after_tools,
)
from agent.state import AgentState
from langgraph.graph import END, StateGraph


@lru_cache
def get_graph():
    """多步 Tool Agent Graph。

    memory_load → pending_gate → agent ⇄ tools → confirm? → response → memory_save
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("memory_load", memory_load_node)
    workflow.add_node("pending_gate", pending_gate_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("confirm", confirm_node)
    workflow.add_node("response", response_node)
    workflow.add_node("memory_save", memory_save_node)

    workflow.set_entry_point("memory_load")
    workflow.add_edge("memory_load", "pending_gate")
    workflow.add_conditional_edges(
        "pending_gate",
        route_after_pending_gate,
        {"confirm": "confirm", "response": "response", "agent": "agent"},
    )
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "confirm": "confirm", "response": "response"},
    )
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        {"agent": "agent", "response": "response"},
    )
    workflow.add_edge("confirm", "response")
    workflow.add_edge("response", "memory_save")
    workflow.add_edge("memory_save", END)

    if CHECKPOINTER_ENABLED:
        return workflow.compile(checkpointer=get_checkpointer())
    return workflow.compile()
