"""Dialect-aware case-insensitive search helpers."""

from __future__ import annotations

from sqlalchemy.sql.elements import ColumnElement

from main_server.config.constants import DB_POSTGRESQL


def case_insensitive_like(column, pattern: str, dialect: str) -> ColumnElement:
    """PostgreSQL uses ILIKE; SQLite uses LIKE (ASCII case-insensitive by default)."""
    if dialect == DB_POSTGRESQL:
        return column.ilike(pattern)
    return column.like(pattern)
