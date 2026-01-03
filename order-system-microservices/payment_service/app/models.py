# File: payment_service/app/models.py

from sqlalchemy import Column, Integer, String, Float, Boolean
from .database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, index=True) # UUID
    amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(String) # SUCCESS / FAILED
    is_successful = Column(Boolean, default=False)