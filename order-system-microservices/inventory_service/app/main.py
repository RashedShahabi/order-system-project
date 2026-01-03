# File: inventory_service/app/main.py

# --- Imports ---
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

# --- Internal Imports ---
from .database import SessionLocal, engine, Base
from .models import StockItem
# Import the helper to start consumer
from .consumers import start_consumer_thread

# --- Database Initialization ---
Base.metadata.create_all(bind=engine)

# --- App Instance ---
app = FastAPI()

# --- Startup Event ---
@app.on_event("startup")
def startup_event():
    """
    When FastAPI starts, we also start the RabbitMQ consumer
    in a background thread to listen for events.
    """
    start_consumer_thread()

# --- Request Models ---
class ItemCreate(BaseModel):
    item_sku: str
    quantity: int

# --- Endpoints ---
@app.get("/")
def root():
    return {"message": "Inventory Service is running (Event-Driven Mode)"}

@app.post("/api/v1/stock/items")
def add_or_update_item(item: ItemCreate):
    """Adds new stock or updates existing stock."""
    db: Session = SessionLocal()
    db_item = db.query(StockItem).filter(StockItem.item_sku == item.item_sku).first()

    if db_item:
        db_item.quantity += item.quantity
    else:
        db_item = StockItem(item_sku=item.item_sku, quantity=item.quantity)
        db.add(db_item)

    db.commit()
    db.refresh(db_item)
    db.close()

    return {
        "status": "ok",
        "item_sku": db_item.item_sku,
        "quantity": db_item.quantity
    }

@app.get("/api/v1/stock/")
def list_items():
    db: Session = SessionLocal()
    items = db.query(StockItem).all()
    db.close()
    return [{"item_sku": i.item_sku, "quantity": i.quantity} for i in items]

@app.get("/api/v1/stock/{sku}")
def get_item(sku: str):
    db: Session = SessionLocal()
    item = db.query(StockItem).filter(StockItem.item_sku == sku).first()
    db.close()
    if not item:
        return {"error": "item not found"}
    return {"item_sku": item.item_sku, "quantity": item.quantity}

# Note: We removed the HTTP endpoints for /reserve and /release 
# because now those actions are handled via RabbitMQ events!