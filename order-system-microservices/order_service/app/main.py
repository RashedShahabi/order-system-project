# File: order_service/app/main.py

import uuid
import json
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

# --- Internal Imports ---
from .database import engine, SessionLocal, Base
from .models import Order
# Import the RabbitMQ producer we just created
from .messaging.bus import RabbitMQProducer

# --- Database Initialization ---
Base.metadata.create_all(bind=engine)

# --- App Instance ---
app = FastAPI()

# --- RabbitMQ Setup ---
# Initialize the producer to send events
event_producer = RabbitMQProducer()

# --- Pydantic Models ---
class OrderRequest(BaseModel):
    """Defines the data model for an incoming order request."""
    item_sku: str
    quantity: int
    amount: float
    idempotency_key: str
    currency: str = "USD"

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints ---

@app.get("/")
def root():
    return {"message": "Order Service is running (Event-Driven Mode)"}

@app.post("/api/v1/orders")
def create_order(req: OrderRequest, db: Session = Depends(get_db)):
    """
    Creates an order asynchronously.
    1. Checks idempotency.
    2. Saves order as 'PENDING'.
    3. Publishes 'order.created' event to RabbitMQ.
    """
    
    # 1. Idempotency Check
    existing_order = db.query(Order).filter(Order.idempotency_key == req.idempotency_key).first()
    if existing_order:
        return {
            "message": "Order already received (Idempotent)",
            "order_id": existing_order.order_id,
            "status": existing_order.status
        }

    # Generate a unique Order ID
    new_order_id = str(uuid.uuid4())

    # 2. Save Order to Database with status 'PENDING'
    # We don't know the result yet, so we wait for events.
    new_order = Order(
        order_id=new_order_id,
        item_sku=req.item_sku,
        quantity=req.quantity,
        amount=req.amount,
        status="PENDING",  # Initial status for Saga
        idempotency_key=req.idempotency_key
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 3. Publish Event to RabbitMQ
    event_payload = {
        "order_id": new_order_id,
        "item_sku": req.item_sku,
        "quantity": req.quantity,
        "amount": req.amount,
        "currency": req.currency
    }
    
    # Routing key 'order.created' tells other services a new order exists
    event_producer.publish(routing_key="order.created", message=event_payload)

    return {
        "status": "PENDING",
        "order_id": new_order_id,
        "message": "Order created and event published. Processing continues in background."
    }

@app.get("/api/v1/orders")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return orders

@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order