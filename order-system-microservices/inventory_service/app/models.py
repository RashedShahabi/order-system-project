from sqlalchemy import Column, Integer, String
from .database import Base # Import the Base class from our database setup

# Defines the ORM model for a stock item in the database.
class StockItem(Base):
    # The name of the database table.
    __tablename__ = "stock_items"

    # Define the table columns.
    id = Column(Integer, primary_key=True, index=True)
    item_sku = Column(String, unique=True, index=True) # Stock Keeping Unit, must be unique.
    quantity = Column(Integer) # The available quantity of the item.
