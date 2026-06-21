from agent.checkpoint_factory import get_checkpointer
from main_server.config.constants import DB_SQLITE


def test_sqlite_checkpointer(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_checkpointer.cache_clear()
    from main_server.config.settings import get_settings

    get_settings.cache_clear()
    saver = get_checkpointer()
    assert saver is not None
    assert get_settings().database.dialect == DB_SQLITE
