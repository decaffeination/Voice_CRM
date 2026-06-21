"""将 SQLite 存量数据迁移到 PostgreSQL。

前置条件
--------
1. 目标 PostgreSQL 已创建空库
2. 已安装 ``psycopg[binary]``

用法::

  python scripts/migrate_sqlite_to_postgres.py \\
    --sqlite main_server/data/sqlite/voice_crm.db \\
    --postgres postgresql+psycopg://voice_crm:voice_crm@localhost:5432/voice_crm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import Engine

import main_server.DB.models  # noqa: F401
from alembic import command
from alembic.config import Config
from main_server.config.settings import PROJECT_ROOT as APP_ROOT
from main_server.DB.base import Base  # noqa: F401 — register metadata via models import


def _run_postgres_migrations(postgres_url: str) -> None:
    cfg = Config(str(APP_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(APP_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(cfg, "head")


def _reflect_tables(engine: Engine) -> MetaData:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return metadata


def _ordered_table_names(metadata: MetaData) -> list[str]:
    return [table.name for table in metadata.sorted_tables]


def _truncate_target(engine: Engine, table_names: list[str]) -> None:
    if not table_names:
        return
    quoted = ", ".join(f'"{name}"' for name in table_names)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))


def _copy_table(
    source: Engine,
    target: Engine,
    table_name: str,
    *,
    batch_size: int = 500,
) -> int:
    source_meta = _reflect_tables(source)
    target_meta = _reflect_tables(target)
    if table_name not in source_meta.tables or table_name not in target_meta.tables:
        return 0

    src_table: Table = source_meta.tables[table_name]
    tgt_table: Table = target_meta.tables[table_name]
    copied = 0

    with source.connect() as src_conn, target.begin() as tgt_conn:
        result = src_conn.execute(select(src_table))
        batch: list[dict] = []
        while True:
            rows = result.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                batch.append(dict(row._mapping))
            if batch:
                tgt_conn.execute(tgt_table.insert(), batch)
                copied += len(batch)
                batch.clear()

    return copied


def _reset_postgres_sequences(target: Engine, table_names: list[str]) -> None:
    inspector = inspect(target)
    with target.begin() as conn:
        for table_name in table_names:
            pk_cols = inspector.get_pk_columns(table_name)
            if len(pk_cols) != 1:
                continue
            pk = pk_cols[0]["name"]
            if "int" not in str(pk_cols[0]["type"]).lower():
                continue
            conn.execute(
                text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', '{pk}'),
                        COALESCE((SELECT MAX({pk}) FROM "{table_name}"), 1),
                        (SELECT COUNT(*) > 0 FROM "{table_name}")
                    )
                    """
                )
            )


def migrate(sqlite_path: Path, postgres_url: str, *, truncate: bool = True) -> None:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite 文件不存在: {sqlite_path}")

    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
    source = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    target = create_engine(postgres_url, pool_pre_ping=True)

    print("Running Alembic on PostgreSQL...")
    _run_postgres_migrations(postgres_url)

    source_meta = _reflect_tables(source)
    table_names = _ordered_table_names(source_meta)
    if truncate:
        print("Truncating target tables...")
        _truncate_target(target, list(reversed(table_names)))

    total = 0
    for table_name in table_names:
        count = _copy_table(source, target, table_name)
        total += count
        print(f"  {table_name}: {count} rows")

    _reset_postgres_sequences(target, table_names)
    print(f"Done. Copied {total} rows to PostgreSQL.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL")
    parser.add_argument(
        "--sqlite",
        default="main_server/data/sqlite/voice_crm.db",
        help="Path to source SQLite database file",
    )
    parser.add_argument(
        "--postgres",
        required=True,
        help="Target PostgreSQL SQLAlchemy URL",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Do not truncate target tables before copy",
    )
    args = parser.parse_args()

    migrate(
        Path(args.sqlite),
        args.postgres,
        truncate=not args.no_truncate,
    )


if __name__ == "__main__":
    main()
