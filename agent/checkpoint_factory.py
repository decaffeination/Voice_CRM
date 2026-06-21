"""LangGraph Checkpointer factory: SQLite or PostgreSQL by app database dialect."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from main_server.config.constants import DB_POSTGRESQL
from main_server.config.settings import PROJECT_ROOT, get_settings

CHECKPOINT_DIR = PROJECT_ROOT / "main_server" / "data" / "checkpoints"
CHECKPOINT_DB = CHECKPOINT_DIR / "agent_checkpoints.db"

_CHECKPOINT_HOLDERS: list[Any] = []


def _normalize_postgres_url(url: str) -> str:
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    return url


def _create_sqlite_checkpointer():
    from langgraph.checkpoint.sqlite import SqliteSaver

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    cm = SqliteSaver.from_conn_string(str(CHECKPOINT_DB))
    saver = cm.__enter__()
    saver.setup()
    _CHECKPOINT_HOLDERS.append(cm)
    return saver


def _create_postgres_checkpointer(url: str):
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(
        conninfo=_normalize_postgres_url(url),
        min_size=1,
        max_size=5,
        open=True,
    )
    saver = PostgresSaver(pool)
    saver.setup()
    _CHECKPOINT_HOLDERS.append(pool)
    return saver


@lru_cache
def get_checkpointer():
    settings = get_settings()
    if settings.database.dialect == DB_POSTGRESQL:
        return _create_postgres_checkpointer(settings.database.effective_url)
    return _create_sqlite_checkpointer()
