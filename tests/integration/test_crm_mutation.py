"""CRM 改删人工确认流测试。"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.nodes.confirm_node import confirm_node, format_write_preview
from agent.state import default_conversation_state
from main_server.config.constants import (
    MUTATION_DELETE,
    MUTATION_UPDATE,
    PENDING_WRITE_AWAITING,
    PENDING_WRITE_DRAFT,
    WRITE_TYPE_CUSTOMER,
    WRITE_TYPE_FOLLOWUP,
)
from main_server.core.auth.user_service import create_user
from main_server.core.auth.permission import Role
from main_server.core.exceptions import PermissionDeniedError
from main_server.CRM.writes.curstomer_write import create_customer
from main_server.CRM.writes.followup_write import create_followup
from main_server.DB import Base, db_session
from main_server.services.crm_service import crm_service
from main_server.utils.init_db import seed_default_user, seed_roles

FIXTURE: dict = {}


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
    seed_roles()
    seed_default_user()

    with db_session() as session:
        user = create_user(
            session,
            username="sales1",
            password="sales123",
            roles=[Role.SALES],
        )
        customer = create_customer(
            session,
            name="测试客户",
            phone="13800000001",
            owner_user_id=user.id,
        )
        followup = create_followup(
            session,
            customer_id=customer["id"],
            content="初次拜访",
            created_by=user.id,
        )
        FIXTURE.clear()
        FIXTURE.update(
            {"user_id": user.id, "customer": customer, "followup": followup}
        )

    yield engine

    Base.metadata.drop_all(bind=engine)
    conn._engine = None
    conn._SessionLocal = None


def _fx() -> dict:
    return FIXTURE


class TestPrepareMutation:
    def test_prepare_update_includes_before(self, memory_db) -> None:
        fx = _fx()
        state = default_conversation_state()
        result = crm_service.prepare_write(
            conversation_state=state,
            turn_count=1,
            user_id=fx["user_id"],
            roles=[Role.SALES],
            write_type=WRITE_TYPE_CUSTOMER,
            action=MUTATION_UPDATE,
            payload={
                "customer_id": fx["customer"]["id"],
                "phone": "13900000002",
            },
        )
        assert result.payload["prepared"] is True
        pending = state["pending_write"]
        assert pending is not None
        assert pending["action"] == MUTATION_UPDATE
        assert pending["before"]["phone"] == "13800000001"
        assert pending["payload"]["phone"] == "13900000002"
        preview = format_write_preview(pending)
        assert "修改客户" in preview
        assert "13800000001" in preview

    def test_prepare_delete_followup(self, memory_db) -> None:
        fx = _fx()
        state = default_conversation_state()
        result = crm_service.prepare_write(
            conversation_state=state,
            turn_count=1,
            user_id=fx["user_id"],
            roles=[Role.SALES],
            write_type=WRITE_TYPE_FOLLOWUP,
            action=MUTATION_DELETE,
            payload={"followup_id": fx["followup"]["id"]},
        )
        assert result.payload["prepared"] is True
        pending = state["pending_write"]
        assert pending["action"] == MUTATION_DELETE
        assert "删除跟进记录" in format_write_preview(pending)


class TestExecuteMutation:
    def test_confirm_update_customer(self, memory_db) -> None:
        fx = _fx()
        state = default_conversation_state()
        state["pending_write"] = {
            "action": MUTATION_UPDATE,
            "type": WRITE_TYPE_CUSTOMER,
            "payload": {
                "customer_id": fx["customer"]["id"],
                "phone": "13700000003",
            },
            "status": PENDING_WRITE_AWAITING,
            "created_at_turn": 1,
        }
        result = confirm_node(
            {
                "intent": "confirm",
                "conversation_state": state,
                "user_id": fx["user_id"],
                "roles": [Role.SALES],
            }
        )
        assert result["tool_result"]["updated"] is True
        updated = crm_service.get_customer_by_id(
            fx["customer"]["id"],
            user_id=fx["user_id"],
            roles=[Role.SALES],
        )
        assert updated["phone"] == "13700000003"

    def test_confirm_delete_followup(self, memory_db) -> None:
        fx = _fx()
        state = default_conversation_state()
        state["pending_write"] = {
            "action": MUTATION_DELETE,
            "type": WRITE_TYPE_FOLLOWUP,
            "payload": {"followup_id": fx["followup"]["id"]},
            "status": PENDING_WRITE_AWAITING,
            "created_at_turn": 1,
        }
        result = confirm_node(
            {
                "intent": "confirm",
                "conversation_state": state,
                "user_id": fx["user_id"],
                "roles": [Role.SALES],
            }
        )
        assert result["tool_result"]["deleted"] is True
        followups = crm_service.list_followups(
            fx["customer"]["id"],
            user_id=fx["user_id"],
            roles=[Role.SALES],
        )
        assert followups == []

    def test_draft_to_awaiting_preview(self, memory_db) -> None:
        fx = _fx()
        state = default_conversation_state()
        state["pending_write"] = {
            "action": MUTATION_UPDATE,
            "type": WRITE_TYPE_CUSTOMER,
            "payload": {
                "customer_id": fx["customer"]["id"],
                "email": "new@example.com",
            },
            "before": fx["customer"],
            "status": PENDING_WRITE_DRAFT,
            "created_at_turn": 1,
        }
        result = confirm_node({"intent": "agent", "conversation_state": state})
        assert result["tool_result"]["awaiting_confirm"] is True
        assert (
            result["conversation_state"]["pending_write"]["status"]
            == PENDING_WRITE_AWAITING
        )

    def test_update_denied_without_access(self, memory_db) -> None:
        fx = _fx()
        with db_session() as session:
            other = create_user(
                session,
                username="other_sales",
                password="sales123",
                roles=[Role.SALES],
            )
            other_id = other.id

        with pytest.raises(PermissionDeniedError):
            crm_service.execute_write(
                WRITE_TYPE_CUSTOMER,
                {
                    "customer_id": fx["customer"]["id"],
                    "phone": "13600000000",
                },
                user_id=other_id,
                roles=[Role.SALES],
                action=MUTATION_UPDATE,
            )
