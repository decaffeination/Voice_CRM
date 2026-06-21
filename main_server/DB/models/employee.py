from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from main_server.DB.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, index=True)
    department = Column(String(128))
    phone = Column(String(64))
    email = Column(String(255))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
