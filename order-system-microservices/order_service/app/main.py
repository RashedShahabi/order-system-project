# File: order_service/app/main.py
import uuid
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from .models import Order
from .messaging.producer import RabbitMQProducer
# --- New Import ---
from .consumers import start_consumer_thread

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Startup Event (فعال کردن گوش‌دهنده) ---
@app.on_event("startup")
def startup_event():
    start_consumer_thread()

class OrderCreate(BaseModel):
    item_sku: str
    quantity: int
    amount: float
    currency: str = "USD"
    idempotency_key: str

@app.get("/")
def root():
    return {"message": "Order Service is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/orders")
def create_order(order_request: OrderCreate, db: Session = Depends(get_db)):
    existing_order = db.query(Order).filter(Order.idempotency_key == order_request.idempotency_key).first()
    if existing_order:
        return {"id": existing_order.id, "order_id": existing_order.order_id, "status": existing_order.status, "message": "Idempotent"}

    order_id = str(uuid.uuid4())
    new_order = Order(
        order_id=order_id,
        item_sku=order_request.item_sku,
        quantity=order_request.quantity,
        amount=order_request.amount,
        currency=order_request.currency,
        idempotency_key=order_request.idempotency_key,
        status="PENDING"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    event = {
        "order_id": order_id,
        "item_sku": new_order.item_sku,
        "quantity": new_order.quantity,
        "amount": new_order.amount,
        "currency": new_order.currency
    }
    
    try:
        producer = RabbitMQProducer()
        producer.publish_event(event)
    except Exception as e:
        print(f"Failed to publish: {e}")

    return {
        "id": new_order.id,
        "order_id": order_id,
        "status": "PENDING",
        "message": "Order created"
    }

@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    # اول سعی کن با UUID پیدا کنی
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    # اگر پیدا نشد و ورودی عدد بود، با ID معمولی پیدا کن (برای پاس کردن تست)
    if not order and order_id.isdigit():
        order = db.query(Order).filter(Order.id == int(order_id)).first()
        
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return {
        "id": order.id,
        "order_id": order.order_id,
        "status": order.status,
        "item_sku": order.item_sku,
        "quantity": order.quantity,
        "amount": order.amount
    }