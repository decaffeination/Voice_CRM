from __future__ import annotations

from sqlalchemy.orm import Session

from main_server.CRM.repository.followup_repo import to_dict
from main_server.DB.models import Followup


def create_followup(
    session: Session,
    *,
    customer_id: int,
    content: str,
    followup_type: str = "note",
    created_by: int | None = None,
) -> dict:
    followup = Followup(
        customer_id=customer_id,
        content=content.strip(),
        followup_type=followup_type,
        created_by=created_by,
    )
    session.add(followup)
    session.flush()
    return to_dict(followup)


def update_followup(
    session: Session,
    followup_id: int,
    *,
    content: str | None = None,
    followup_type: str | None = None,
) -> dict:
    followup = session.query(Followup).filter(Followup.id == followup_id).first()
    if followup is None:
        raise ValueError(f"跟进不存在: id={followup_id}")
    if content is not None:
        followup.content = content.strip()
    if followup_type is not None:
        followup.followup_type = followup_type
    session.flush()
    return to_dict(followup)


def delete_followup(session: Session, followup_id: int) -> dict:
    followup = session.query(Followup).filter(Followup.id == followup_id).first()
    if followup is None:
        raise ValueError(f"跟进不存在: id={followup_id}")
    data = to_dict(followup)
    session.delete(followup)
    session.flush()
    return data
