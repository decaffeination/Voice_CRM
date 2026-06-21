"""Deprecated alias — use ``main_server.DB`` instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "main_server.CRM.sql_connection is deprecated; import from main_server.DB",
    DeprecationWarning,
    stacklevel=2,
)

from main_server.DB import (  # noqa: E402, F401
    Base,
    db_session,
    get_db,
    get_engine,
    get_session_factory,
)

__all__ = [
    "Base",
    "db_session",
    "get_db",
    "get_engine",
    "get_session_factory",
]
