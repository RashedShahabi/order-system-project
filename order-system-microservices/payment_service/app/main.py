# --- Imports ---
from fastapi import FastAPI
from pydantic import BaseModel

# --- App Instance ---
app = FastAPI()

# --- Request Models ---
class PaymentRequest(BaseModel):
    """Defines the request model for payment authorization."""
    amount: float

# --- Endpoints ---
@app.get("/")
def root():
    """Health check endpoint to verify the service is running."""
    return {"message": "Payment service is running"}

@app.post("/api/v1/payments/authorize")
def authorize_payment(req: PaymentRequest):
    """
    Simulates payment authorization.
    - Approves if amount < 1000.
    - Declines if amount >= 1000.
    """
    if req.amount < 1000:
        return {"authorized": True}
    else:
        return {"authorized": False}
