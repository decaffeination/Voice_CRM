from sqlalchemy.dialects import postgresql, sqlite

from main_server.config.constants import DB_POSTGRESQL, DB_SQLITE
from main_server.DB.models import Customer
from main_server.DB.search import case_insensitive_like


def test_postgresql_uses_ilike() -> None:
    expr = case_insensitive_like(Customer.name, "%acme%", DB_POSTGRESQL)
    compiled = str(expr.compile(dialect=postgresql.dialect()))
    assert "ILIKE" in compiled.upper()


def test_sqlite_uses_like() -> None:
    expr = case_insensitive_like(Customer.name, "%acme%", DB_SQLITE)
    compiled = str(expr.compile(dialect=sqlite.dialect()))
    assert "ILIKE" not in compiled.upper()
    assert "LIKE" in compiled.upper()
