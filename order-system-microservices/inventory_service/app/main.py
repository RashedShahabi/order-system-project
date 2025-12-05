# --- Imports ---
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session # For database session management

# Internal imports from sibling modules
from .database import SessionLocal, engine
from .models import Base, StockItem

# --- Database Initialization ---
# Create database tables defined in models.py if they don't exist
Base.metadata.create_all(bind=engine)

# --- App Instance ---
app = FastAPI()

# --- Request Models ---
class ItemCreate(BaseModel):
    """Pydantic model for creating or updating an item's stock."""
    item_sku: str
    quantity: int

class ReserveRequest(BaseModel):
    """Pydantic model for requesting to reserve stock."""
    item_sku: str
    quantity: int

class ReleaseRequest(BaseModel):
    """Pydantic model for requesting to release/add back stock."""
    item_sku: str
    quantity: int

# --- Endpoints ---
@app.get("/")
def root():
    """Health check endpoint to confirm the inventory service is operational."""
    return {"message": "Inventory service is running"}

@app.post("/api/v1/stock/items")
def add_or_update_item(item: ItemCreate):
    """
    Adds new stock for an item or updates existing stock (upsert operation).
    - If item exists, quantity is added.
    - If item does not exist, a new item is created.
    """
    db: Session = SessionLocal() # Get a new database session
    db_item = db.query(StockItem).filter(StockItem.item_sku == item.item_sku).first()

    if db_item:
        db_item.quantity += item.quantity # Update existing item's quantity
    else:
        db_item = StockItem(item_sku=item.item_sku, quantity=item.quantity) # Create new item
        db.add(db_item)

    db.commit()      # Save changes to the database
    db.refresh(db_item) # Refresh the object to get updated data
    db.close()       # Close the database session

    return {
        "status": "ok",
        "item_sku": db_item.item_sku,
        "quantity": db_item.quantity
    }

@app.get("/api/v1/stock/")
def list_items():
    """Retrieves a list of all stock items with their current quantities."""
    db: Session = SessionLocal()
    items = db.query(StockItem).all() # Fetch all stock items
    db.close()
    # Format and return the list of items
    return [{"item_sku": item.item_sku, "quantity": item.quantity} for item in items]

@app.get("/api/v1/stock/{sku}")
def get_item(sku: str):
    """Retrieves the details (item_sku and quantity) for a specific item by SKU."""
    db: Session = SessionLocal()
    item = db.query(StockItem).filter(StockItem.item_sku == sku).first() # Find item by SKU
    db.close()

    if not item:
        return {"error": "item not found"}

    return {"item_sku": item.item_sku, "quantity": item.quantity}

@app.post("/api/v1/stock/reserve")
def reserve_stock(req: ReserveRequest):
    """
    Reserves a specified quantity of an item from stock.
    - Decrements quantity if available.
    - Returns error if item not found or insufficient stock.
    """
    db: Session = SessionLocal()
    item = db.query(StockItem).filter(StockItem.item_sku == req.item_sku).first()

    if not item:
        db.close()
        return {"error": "item not found"}

    if item.quantity < req.quantity:
        db.close()
        return {"error": "not enough stock"}

    item.quantity -= req.quantity # Decrease stock quantity
    db.commit()
    db.refresh(item)
    db.close()

    return {"status": "reserved", "item_sku": item.item_sku, "remaining": item.quantity}

@app.post("/api/v1/stock/release")
def release_stock(req: ReleaseRequest):
    """
    Releases a specified quantity of an item, adding it back to stock.
    - Increments quantity.
    - Returns error if item not found.
    """
    db: Session = SessionLocal()
    item = db.query(StockItem).filter(StockItem.item_sku == req.item_sku).first()

    if not item:
        db.close()
        return {"error": "item not found"}

    item.quantity += req.quantity # Increase stock quantity
    db.commit()
    db.refresh(item)
    db.close()

    return {"status": "released", "item_sku": item.item_sku, "quantity": item.quantity}
