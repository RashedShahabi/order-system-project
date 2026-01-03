from sqlalchemy import Column, Integer, String, Float, Boolean
from .database import Base

# Defines the ORM model for a 'Payment' transaction.
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, index=True) # Links the payment to a specific order.
    amount = Column(Float) # The amount to be charged.
    currency = Column(String, default="USD")
    status = Column(String) # Status of the payment (e.g., "success", "failed").
    is_successful = Column(Boolean) # Simplified flag for easy checks.