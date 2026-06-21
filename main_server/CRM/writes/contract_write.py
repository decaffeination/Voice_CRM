from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from main_server.CRM.repository.contract_repo import to_dict
from main_server.DB.models import Contract


def create_contract(
    session: Session,
    *,
    customer_id: int,
    title: str,
    amount: float = 0,
    status: str = "draft",
    signed_at: datetime | None = None,
    content: str | None = None,
    created_by: int | None = None,
) -> dict:
    contract = Contract(
        customer_id=customer_id,
        title=title.strip(),
        amount=amount,
        status=status,
        signed_at=signed_at,
        content=content,
        created_by=created_by,
    )
    session.add(contract)
    session.flush()
    return to_dict(contract)


_CONTRACT_UPDATE_FIELDS = frozenset(
    {"title", "amount", "status", "signed_at", "content"}
)


def update_contract(
    session: Session,
    contract_id: int,
    *,
    updates: dict,
) -> dict:
    contract = session.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise ValueError(f"合同不存在: id={contract_id}")
    for key, value in updates.items():
        if key not in _CONTRACT_UPDATE_FIELDS:
            continue
        if value is not None:
            setattr(contract, key, value)
    session.flush()
    return to_dict(contract)


def delete_contract(session: Session, contract_id: int) -> dict:
    contract = session.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise ValueError(f"合同不存在: id={contract_id}")
    data = to_dict(contract)
    session.delete(contract)
    session.flush()
    return data
