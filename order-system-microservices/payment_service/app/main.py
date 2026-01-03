# File: payment_service/app/main.py

# --- Imports ---
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# --- Internal Imports ---
from .database import engine, Base, get_db
from .models import Payment
# Import the helper to start consumer
from .consumers import start_consumer_thread

# --- Database Initialization ---
Base.metadata.create_all(bind=engine)

# --- App Instance ---
app = FastAPI()

# --- Startup Event (New for Phase 2) ---
@app.on_event("startup")
def startup_event():
    """Start the RabbitMQ consumer when the app starts."""
    start_consumer_thread()

# --- Request Models ---
class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    currency: str = "USD"

# --- Endpoints ---
@app.get("/")
def root():
    return {"message": "Payment Service is running (Event-Driven Mode)"}

# Note: The HTTP endpoint below is technically not used in the automated RabbitMQ flow,
# but we keep it for manual testing or debugging if needed.
@app.post("/api/v1/payments/authorize")
def authorize_payment_manual(req: PaymentRequest, db: Session = Depends(get_db)):
    """Manual trigger for payment (HTTP)."""
    is_auth = req.amount < 1000
    status = "success" if is_auth else "failed"

    new_payment = Payment(
        order_id=req.order_id,
        amount=req.amount,
        currency=req.currency,
        status=status,
        is_successful=is_auth
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return {"authorized": is_auth, "payment_id": new_payment.id}