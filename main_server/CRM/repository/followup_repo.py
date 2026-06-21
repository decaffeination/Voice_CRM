from __future__ import annotations

from sqlalchemy.orm import Session

from main_server.DB.models import Followup


def get_by_id(session: Session, followup_id: int) -> Followup | None:
    return session.query(Followup).filter(Followup.id == followup_id).first()


def list_by_customer(
    session: Session, customer_id: int, limit: int = 20
) -> list[Followup]:
    return (
        session.query(Followup)
        .filter(Followup.customer_id == customer_id)
        .order_by(Followup.created_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_by_customer(session: Session, customer_id: int) -> Followup | None:
    return (
        session.query(Followup)
        .filter(Followup.customer_id == customer_id)
        .order_by(Followup.created_at.desc())
        .first()
    )


def to_dict(followup: Followup) -> dict:
    return {
        "id": followup.id,
        "customer_id": followup.customer_id,
        "content": followup.content,
        "followup_type": followup.followup_type,
        "created_by": followup.created_by,
        "created_at": followup.created_at.isoformat() if followup.created_at else None,
    }
