"""SQLAlchemy declarative Base，供 ORM 模型与 connection 共用。"""

from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()
