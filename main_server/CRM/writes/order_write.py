from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from main_server.CRM.repository.order_repo import get_by_id, to_dict
from main_server.DB.models import Order

_ORDER_UPDATE_FIELDS = frozenset(
    {"title", "amount", "status", "order_date", "content", "contract_id"}
)


def update_order(
    session: Session,
    order_id: int,
    *,
    updates: dict,
) -> dict:
    order = get_by_id(session, order_id)
    if order is None:
        raise ValueError(f"订单不存在: id={order_id}")
    for key, value in updates.items():
        if key not in _ORDER_UPDATE_FIELDS:
            continue
        if value is None:
            continue
        if key == "order_date" and isinstance(value, str):
            setattr(order, key, datetime.fromisoformat(value))
        else:
            setattr(order, key, value)
    session.flush()
    return to_dict(order)


def delete_order(session: Session, order_id: int) -> dict:
    order = get_by_id(session, order_id)
    if order is None:
        raise ValueError(f"订单不存在: id={order_id}")
    data = to_dict(order)
    session.delete(order)
    session.flush()
    return data
