from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from main_server.config.settings import get_settings
from main_server.DB.models import Customer
from main_server.DB.search import case_insensitive_like


def get_by_id(session: Session, customer_id: int) -> Customer | None:
    return session.query(Customer).filter(Customer.id == customer_id).first()


def search_by_name(
    session: Session,
    name: str,
    limit: int = 10,
    owner_user_id: int | None = None,
    owner_user_ids: list[int] | None = None,
) -> list[Customer]:
    keyword = name.strip()
    if not keyword:
        return []
    pattern = f"%{keyword}%"
    dialect = get_settings().database.dialect
    query = session.query(Customer).filter(
        case_insensitive_like(Customer.name, pattern, dialect)
    )
    if owner_user_ids is not None:
        if not owner_user_ids:
            return []
        query = query.filter(Customer.owner_user_id.in_(owner_user_ids))
    elif owner_user_id is not None:
        query = query.filter(Customer.owner_user_id == owner_user_id)
    return query.order_by(Customer.updated_at.desc()).limit(limit).all()


def list_by_owner_ids(session: Session, owner_user_ids: list[int]) -> list[Customer]:
    if not owner_user_ids:
        return []
    return (
        session.query(Customer)
        .filter(Customer.owner_user_id.in_(owner_user_ids))
        .order_by(Customer.updated_at.desc())
        .all()
    )


def list_by_owner(session: Session, owner_user_id: int) -> list[Customer]:
    return (
        session.query(Customer)
        .filter(Customer.owner_user_id == owner_user_id)
        .order_by(Customer.updated_at.desc())
        .all()
    )


def list_recent_updated(
    session: Session,
    days: int = 30,
    owner_user_id: int | None = None,
    owner_user_ids: list[int] | None = None,
) -> list[Customer]:
    since = datetime.now() - timedelta(days=days)
    query = session.query(Customer).filter(Customer.updated_at >= since)
    if owner_user_ids is not None:
        if not owner_user_ids:
            return []
        query = query.filter(Customer.owner_user_id.in_(owner_user_ids))
    elif owner_user_id is not None:
        query = query.filter(Customer.owner_user_id == owner_user_id)
    return query.order_by(Customer.updated_at.desc()).all()


def list_by_employee_user_id(session: Session, user_id: int) -> list[Customer]:
    return (
        session.query(Customer)
        .filter(Customer.owner_user_id == user_id)
        .order_by(Customer.name.asc())
        .all()
    )


def list_all(session: Session, *, limit: int = 100) -> list[Customer]:
    return (
        session.query(Customer)
        .order_by(Customer.updated_at.desc())
        .limit(limit)
        .all()
    )


def to_dict(customer: Customer) -> dict:
    return {
        "id": customer.id,
        "name": customer.name,
        "contact_person": customer.contact_person,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address,
        "status": customer.status,
        "owner_user_id": customer.owner_user_id,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
    }
