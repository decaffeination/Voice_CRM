"""User ORM repository."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from main_server.core.auth.permission import Role as RoleCode
from main_server.DB.models import Role as RoleModel, User


def get_by_id(session: Session, user_id: int) -> User | None:
    return (
        session.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == user_id)
        .first()
    )


def get_by_username(session: Session, username: str) -> User | None:
    return (
        session.query(User)
        .options(joinedload(User.roles))
        .filter(User.username == username)
        .first()
    )


def get_by_username_exists(session: Session, username: str) -> bool:
    return session.query(User).filter(User.username == username).first() is not None


def get_roles_by_codes(session: Session, codes: list[str]) -> list[RoleModel]:
    return session.query(RoleModel).filter(RoleModel.code.in_(codes)).all()


def count_admin_users(session: Session) -> int:
    return (
        session.query(User)
        .join(User.roles)
        .filter(RoleModel.code == RoleCode.ADMIN)
        .distinct()
        .count()
    )


def purge_user_dependents(session: Session, user_id: int) -> None:
    from main_server.DB.models.chat_message import ChatMessageORM
    from main_server.DB.models.chat_session import ChatSessionORM
    from main_server.DB.models.chat_state import ChatStateORM
    from main_server.DB.models.chat_summary import ChatSummaryORM
    from main_server.DB.models.customer import Customer
    from main_server.DB.models.employee import Employee

    session_ids = [
        row[0]
        for row in session.query(ChatSessionORM.session_id)
        .filter(ChatSessionORM.user_id == user_id)
        .all()
    ]
    if session_ids:
        session.query(ChatMessageORM).filter(
            ChatMessageORM.session_id.in_(session_ids)
        ).delete(synchronize_session=False)
        session.query(ChatStateORM).filter(
            ChatStateORM.session_id.in_(session_ids)
        ).delete(synchronize_session=False)
        session.query(ChatSummaryORM).filter(
            ChatSummaryORM.session_id.in_(session_ids)
        ).delete(synchronize_session=False)
        session.query(ChatSessionORM).filter(
            ChatSessionORM.user_id == user_id
        ).delete(synchronize_session=False)

    session.query(Employee).filter(Employee.user_id == user_id).update(
        {Employee.user_id: None},
        synchronize_session=False,
    )
    session.query(Customer).filter(Customer.owner_user_id == user_id).update(
        {Customer.owner_user_id: None},
        synchronize_session=False,
    )
