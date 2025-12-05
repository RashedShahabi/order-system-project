# In file: order-system-microservices/order_service/app/main.py

import uuid
# ---------------------------------

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests

from .database import SessionLocal, engine
from .models import Base, Order

# Create database tables on startup if they don't exist.
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Service URLs for inter-service communication.
INVENTORY_URL = "http://inventory_service:8000/api/v1/stock"
PAYMENT_URL = "http://payment_service:8000/api/v1/payments"


class OrderRequest(BaseModel):
    """Defines the data model for an incoming order request."""
    item_sku: str
    quantity: int
    amount: float
    idempotency_key: str
# -------------------------------------------------------------

@app.get("/")
def root():
    """Health check endpoint."""
    return {"message": "Order service is running"}

# Creates a new order by orchestrating calls to Inventory and Payment services.
@app.post("/api/v1/orders")
def create_order(req: OrderRequest):
    database: Session = SessionLocal()

    # 1. Idempotency Check: Ensure this request hasn't been processed before.
    existing_order = database.query(Order).filter(Order.idempotency_key == req.idempotency_key).first()
    if existing_order:
        database.close()
        return {
            "status": existing_order.status,
            "order_id": existing_order.order_id
        }

    # --- CHANGE 3: GENERATE A NEW, UNIQUE ORDER ID ---
    new_order_id = str(uuid.uuid4())
    # --------------------------------------------------

    # 2. Reserve stock by calling the Inventory Service.
    try:
        reserve_response = requests.post(
            f"{INVENTORY_URL}/reserve",
            json={"item_sku": req.item_sku, "quantity": req.quantity}
        )
        reserve_response.raise_for_status() # Raises an exception for 4xx/5xx status codes
        if "error" in reserve_response.json():
            raise requests.exceptions.RequestException("Stock reservation failed")
    except requests.exceptions.RequestException:
        database.close()
        return {"status": "failed", "error": "Inventory service communication error or reservation failed"}


    # 3. Authorize payment by calling the Payment Service.
    try:
        payment_response = requests.post(
            f"{PAYMENT_URL}/authorize",
            # --- CHANGE 4: USE THE NEWLY GENERATED ID ---
            json={"order_id": new_order_id, "amount": req.amount}
            # --------------------------------------------
        )
        payment_response.raise_for_status()
        payment_data = payment_response.json()
    except requests.exceptions.RequestException:
        # Compensating action: Release stock if payment service is unreachable.
        requests.post(f"{INVENTORY_URL}/release", json={"item_sku": req.item_sku, "quantity": req.quantity})
        database.close()
        return {"status": "failed", "error": "Payment service communication error"}

    authorized = payment_data.get("authorized", False)

    if not authorized:
        # Compensating action: Release stock if payment is declined.
        requests.post(
            f"{INVENTORY_URL}/release",
            json={"item_sku": req.item_sku, "quantity": req.quantity}
        )

        # Save the order as 'failed'.
        status = "failed"
    else:
        # 4. Success: The order is confirmed.
        status = "confirmed"

    # Save the final order state to the database.
    new_order = Order(
        # --- CHANGE 5: USE THE NEWLY GENERATED ID ---
        order_id=new_order_id,
        # --------------------------------------------
        item_sku=req.item_sku,
        quantity=req.quantity,
        amount=req.amount,
        status=status,
        idempotency_key=req.idempotency_key
    )
    database.add(new_order)
    database.commit()
    database.close()

    # --- CHANGE 6: RETURN THE NEWLY GENERATED ID ---
    return {"status": status, "order_id": new_order_id}
    # ---------------------------------------------

# Retrieves a single order by its ID.
@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: str):
    database: Session = SessionLocal()
    order = database.query(Order).filter(Order.order_id == order_id).first()
    database.close()

    if not order:
        return {"error": "Order not found"}

    return {
        "order_id": order.order_id,
        "item_sku": order.item_sku,
        "quantity": order.quantity,
        "amount": order.amount,
        "status": order.status
    }

# Retrieves a list of all orders.
@app.get("/api/v1/orders")
def list_orders():
    database: Session = SessionLocal()
    orders = database.query(Order).all()
    database.close()

    # Format the list of orders for the response.
    return [
        {
            "order_id": o.order_id,
            "item_sku": o.item_sku,
            "quantity": o.quantity,
            "amount": o.amount,
            "status": o.status
        }
        for o in orders
    ]
