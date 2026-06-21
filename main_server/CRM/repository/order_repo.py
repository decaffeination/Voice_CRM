from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from main_server.DB.models import Order


def get_by_id(session: Session, order_id: int) -> Order | None:
    return session.query(Order).filter(Order.id == order_id).first()


def get_latest_by_customer(session: Session, customer_id: int) -> Order | None:
    return (
        session.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.order_date.desc(), Order.created_at.desc())
        .first()
    )


def list_by_customer(session: Session, customer_id: int, limit: int = 10) -> list[Order]:
    return (
        session.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.order_date.desc(), Order.created_at.desc())
        .limit(limit)
        .all()
    )


def create_order(
    session: Session,
    *,
    customer_id: int,
    title: str,
    amount: float = 0,
    status: str = "pending",
    contract_id: int | None = None,
    order_date: datetime | None = None,
    content: str | None = None,
    created_by: int | None = None,
) -> dict:
    order = Order(
        customer_id=customer_id,
        contract_id=contract_id,
        title=title.strip(),
        amount=amount,
        status=status,
        order_date=order_date,
        content=content,
        created_by=created_by,
    )
    session.add(order)
    session.flush()
    return to_dict(order)


def to_dict(order: Order) -> dict:
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "contract_id": order.contract_id,
        "title": order.title,
        "amount": order.amount,
        "status": order.status,
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "content": order.content,
        "created_by": order.created_by,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }
