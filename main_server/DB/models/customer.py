from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from main_server.DB.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    contact_person = Column(String(128))
    phone = Column(String(64))
    email = Column(String(255))
    address = Column(String(512))
    status = Column(String(32), default="active")
    owner_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
