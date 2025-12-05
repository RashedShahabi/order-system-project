from sqlalchemy import Column, Integer, String, Float
from .database import Base # Import the Base class from our database setup

# Defines the ORM model for an 'Order' stored in the database.
class Order(Base):
    # The name of the database table.
    __tablename__ = "orders"

    # Define the table columns.
    id = Column(Integer, primary_key=True, index=True) # Auto-incrementing primary key.
    order_id = Column(String, unique=True) # Business-level order identifier.
    item_sku = Column(String) # SKU of the item being ordered.
    quantity = Column(Integer) # Quantity of the item ordered.
    amount = Column(Float) # Total amount for the order.
    status = Column(String) # Order status (e.g., "confirmed", "failed").
    idempotency_key = Column(String, unique=True) # Key to prevent duplicate processing.
