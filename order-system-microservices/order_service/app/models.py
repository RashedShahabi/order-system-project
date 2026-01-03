# File: order_service/app/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    item_sku = Column(String, index=True)
    quantity = Column(Integer)
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String, default="PENDING")
    
    # --- FIX IS HERE: Added this missing column ---
    idempotency_key = Column(String, unique=True, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())