"""LangGraph runtime Checkpointer (optional, not business Memory).

Business session state is persisted via ``agent/nodes/memory_node.py``.
This module is for Human-in-the-loop / interrupt recovery when enabled.
"""

from __future__ import annotations

from agent.checkpoint_factory import (
    CHECKPOINT_DIR,
    CHECKPOINT_DB,
    get_checkpointer,
)

# Graph default off; set True and compile with checkpointer in graph.py
CHECKPOINTER_ENABLED = False

__all__ = [
    "CHECKPOINT_DIR",
    "CHECKPOINT_DB",
    "CHECKPOINTER_ENABLED",
    "get_checkpointer",
]
