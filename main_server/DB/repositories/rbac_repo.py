"""RBAC repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from main_server.DB.models import PermissionORM, Role
from main_server.DB.models.permission import role_permissions


def list_permissions(session: Session) -> list[PermissionORM]:
    return (
        session.query(PermissionORM)
        .order_by(PermissionORM.sort_order.asc(), PermissionORM.code.asc())
        .all()
    )


def upsert_permission(
    session: Session,
    *,
    code: str,
    label: str,
    parent_code: str | None,
    sort_order: int,
) -> PermissionORM:
    row = session.query(PermissionORM).filter(PermissionORM.code == code).first()
    if row is None:
        row = PermissionORM(
            code=code,
            label=label,
            parent_code=parent_code,
            sort_order=sort_order,
        )
        session.add(row)
    else:
        row.label = label
        row.parent_code = parent_code
        row.sort_order = sort_order
    session.flush()
    return row


def get_role_by_code(session: Session, role_code: str) -> Role | None:
    return session.query(Role).filter(Role.code == role_code).first()


def get_role_permission_codes(session: Session, role_id: int) -> list[str]:
    rows = (
        session.query(role_permissions.c.permission_code)
        .filter(role_permissions.c.role_id == role_id)
        .all()
    )
    return [row[0] for row in rows]


def replace_role_permissions(
    session: Session, role_id: int, permission_codes: list[str]
) -> None:
    session.query(role_permissions).filter(
        role_permissions.c.role_id == role_id
    ).delete(synchronize_session=False)
    for code in permission_codes:
        session.execute(
            role_permissions.insert().values(
                role_id=role_id,
                permission_code=code,
            )
        )
    session.flush()


def role_has_any_permissions(session: Session, role_id: int) -> bool:
    return (
        session.query(role_permissions.c.permission_code)
        .filter(role_permissions.c.role_id == role_id)
        .first()
        is not None
    )
