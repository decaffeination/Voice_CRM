"""Memory 节点与 Graph 状态源测试。"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.checkpointer import CHECKPOINTER_ENABLED
from agent.graph import get_graph
from agent.nodes.memory_node import memory_load_node, memory_save_node
from agent.state import default_conversation_state
from main_server.memory.memory_manager import memory_manager
from main_server.memory.memory_schema import ActorContext, TurnContext
from main_server.DB import Base


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
    yield engine
    Base.metadata.drop_all(bind=engine)
    conn._engine = None
    conn._SessionLocal = None
    get_graph.cache_clear()


class TestMemoryNodes:
    def test_load_increments_turn_count(self, memory_db) -> None:
        session_id = str(uuid.uuid4())
        state = memory_manager.load_state(session_id)
        state["turn_count"] = 2
        memory_manager.save_state(session_id, state)

        loaded = memory_load_node(
            {
                "session_id": session_id,
                "user_input": "你好",
                "channel": "text",
            }
        )
        assert loaded["conversation_state"]["turn_count"] == 3
        assert loaded["messages"][-1] == {"role": "user", "content": "你好"}

    def test_save_persists_history_and_state(self, memory_db) -> None:
        session_id = str(uuid.uuid4())
        conversation_state = default_conversation_state()
        conversation_state["turn_count"] = 1
        conversation_state["current_intent"] = "chitchat"

        memory_save_node(
            {
                "session_id": session_id,
                "user_input": "问题",
                "channel": "text",
                "final_response": "回答",
                "conversation_state": conversation_state,
            }
        )

        history = memory_manager.load_history(session_id)
        assert len(history) == 2
        assert history[0].content == "问题"
        assert history[1].content == "回答"

        saved_state = memory_manager.load_state(session_id)
        assert saved_state["turn_count"] == 1
        assert saved_state["current_intent"] == "chitchat"

    def test_roundtrip_load_save_load(self, memory_db) -> None:
        session_id = str(uuid.uuid4())

        first_load = memory_load_node(
            {"session_id": session_id, "user_input": "第一句", "channel": "text"}
        )
        memory_save_node(
            {
                "session_id": session_id,
                "user_input": "第一句",
                "channel": "text",
                "final_response": "回复一",
                "conversation_state": first_load["conversation_state"],
            }
        )

        second_load = memory_load_node(
            {"session_id": session_id, "user_input": "第二句", "channel": "text"}
        )
        assert second_load["conversation_state"]["turn_count"] == 2
        assert any(m["content"] == "回复一" for m in second_load["messages"])


class TestGraphStateSource:
    def test_checkpointer_disabled_by_default(self) -> None:
        assert CHECKPOINTER_ENABLED is False

    def test_graph_compiles_without_checkpointer(self, memory_db) -> None:
        graph = get_graph()
        assert graph.checkpointer is None

    def test_turn_context_has_no_memory_field(self) -> None:
        assert "memory" not in TurnContext.model_fields
