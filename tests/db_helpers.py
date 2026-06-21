"""测试数据库夹具辅助。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from main_server.config.settings import PROJECT_ROOT, get_settings
from main_server.DB.engine_factory import create_database_engine


def resolve_test_database_url(tmp_path: Path) -> str:
    env_url = os.environ.get("DATABASE_URL", "").strip()
    if env_url:
        return env_url
    db_path = tmp_path / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


def is_postgresql_url(url: str) -> bool:
    return url.startswith("postgresql")


def reset_connection_cache() -> None:
    import main_server.DB.connection as conn

    if conn._engine is not None:
        conn._engine.dispose()
    conn._engine = None
    conn._SessionLocal = None
    get_settings.cache_clear()


def run_migrations_for_url(url: str) -> None:
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")


def setup_test_engine(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
) -> tuple[Engine, Any]:
    import main_server.DB.connection as conn

    reset_connection_cache()
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    engine = create_database_engine(url)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    conn._engine = engine
    conn._SessionLocal = session_factory

    run_migrations_for_url(url)
    return engine, conn


def teardown_test_engine(conn: Any, engine: Engine) -> None:
    engine.dispose()
    conn._engine = None
    conn._SessionLocal = None
    get_settings.cache_clear()
