from __future__ import annotations

from sqlalchemy.orm import Session

from main_server.DB.models import Contract


def get_by_id(session: Session, contract_id: int) -> Contract | None:
    return session.query(Contract).filter(Contract.id == contract_id).first()


def get_latest_by_customer(session: Session, customer_id: int) -> Contract | None:
    return (
        session.query(Contract)
        .filter(Contract.customer_id == customer_id)
        .order_by(Contract.signed_at.desc(), Contract.created_at.desc())
        .first()
    )


def list_by_customer(
    session: Session, customer_id: int, limit: int = 10
) -> list[Contract]:
    return (
        session.query(Contract)
        .filter(Contract.customer_id == customer_id)
        .order_by(Contract.signed_at.desc(), Contract.created_at.desc())
        .limit(limit)
        .all()
    )


def to_dict(contract: Contract) -> dict:
    return {
        "id": contract.id,
        "customer_id": contract.customer_id,
        "title": contract.title,
        "amount": contract.amount,
        "status": contract.status,
        "signed_at": contract.signed_at.isoformat() if contract.signed_at else None,
        "content": contract.content,
        "created_by": contract.created_by,
        "created_at": contract.created_at.isoformat() if contract.created_at else None,
    }
