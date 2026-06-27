"""RBAC 权限 ORM。"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from main_server.DB.base import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_code",
        String(64),
        ForeignKey("permissions.code", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class PermissionORM(Base):
    __tablename__ = "permissions"

    code = Column(String(64), primary_key=True)
    label = Column(String(128), nullable=False)
    parent_code = Column(String(64), ForeignKey("permissions.code"), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    children = relationship(
        "PermissionORM",
        backref="parent",
        remote_side=[code],
        foreign_keys=[parent_code],
    )


# 让 Role 模型可引用 role_permissions（在 role.py 中不重复定义）
RolePermissionLink = role_permissions
