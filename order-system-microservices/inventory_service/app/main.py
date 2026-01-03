# File: inventory_service/app/main.py

# --- Imports ---
from fastapi import FastAPI, Depends, HTTPException
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

# --- Dependency (Database Session) ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Startup Event ---
@app.on_event("startup")
def startup_event():
    """
    When FastAPI starts, we also start the RabbitMQ consumer
    in a background thread to listen for events.
    """
    start_consumer_thread()

# --- Request Models ---
class StockItemCreate(BaseModel):
    item_sku: str
    quantity: int

# --- Endpoints ---

@app.get("/")
def root():
    return {"message": "Inventory Service is running (Event-Driven Mode)"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/stock/items")
def create_stock_item(item: StockItemCreate, db: Session = Depends(get_db)):
    # 1. Check if item exists
    db_item = db.query(StockItem).filter(StockItem.item_sku == item.item_sku).first()
    
    if db_item:
        # 2. Update existing quantity
        db_item.quantity = item.quantity
    else:
        # 3. Create new item
        db_item = StockItem(item_sku=item.item_sku, quantity=item.quantity)
        db.add(db_item)
    
    # 4. CRITICAL: Commit to save changes!
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/api/v1/stock/")
def list_items(db: Session = Depends(get_db)):
    items = db.query(StockItem).all()
    return [{"item_sku": i.item_sku, "quantity": i.quantity} for i in items]

# --- FIX IS HERE: Added /items/ to the path ---
@app.get("/api/v1/stock/items/{item_sku}")
def get_stock_item(item_sku: str, db: Session = Depends(get_db)):
    item = db.query(StockItem).filter(StockItem.item_sku == item_sku).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not Found")
    return item