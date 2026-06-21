"""数据库 dialect 展示名与健康检查辅助。"""

from __future__ import annotations

from main_server.config.constants import DB_POSTGRESQL, DB_SQLITE


def database_display_name(dialect: str) -> str:
    if dialect == DB_POSTGRESQL:
        return "PostgreSQL"
    if dialect == DB_SQLITE:
        return "SQLite"
    return dialect
