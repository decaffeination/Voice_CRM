from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from main_server.DB.base import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"))
    title = Column(String(255), nullable=False)
    amount = Column(Float, default=0)
    status = Column(String(32), default="pending")
    order_date = Column(DateTime)
    content = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
