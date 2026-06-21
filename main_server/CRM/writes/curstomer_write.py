from __future__ import annotations

from sqlalchemy.orm import Session

from main_server.CRM.repository.customer_repo import to_dict
from main_server.DB.models import Customer


def create_customer(
    session: Session,
    *,
    name: str,
    contact_person: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
    status: str = "active",
    owner_user_id: int | None = None,
) -> dict:
    customer = Customer(
        name=name.strip(),
        contact_person=contact_person,
        phone=phone,
        email=email,
        address=address,
        status=status,
        owner_user_id=owner_user_id,
    )
    session.add(customer)
    session.flush()
    return to_dict(customer)


_CUSTOMER_UPDATE_FIELDS = frozenset(
    {"name", "contact_person", "phone", "email", "address", "status"}
)


def update_customer(
    session: Session,
    customer_id: int,
    *,
    updates: dict,
) -> dict:
    customer = session.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise ValueError(f"客户不存在: id={customer_id}")
    for key, value in updates.items():
        if key not in _CUSTOMER_UPDATE_FIELDS:
            continue
        if value is not None:
            setattr(customer, key, value.strip() if isinstance(value, str) else value)
    session.flush()
    return to_dict(customer)


def archive_customer(session: Session, customer_id: int) -> dict:
    customer = session.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise ValueError(f"客户不存在: id={customer_id}")
    customer.status = "archived"
    session.flush()
    return to_dict(customer)
