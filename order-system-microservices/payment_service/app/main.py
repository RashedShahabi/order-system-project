import uuid
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import Payment
from .consumers import start_consumer_thread

# 1. ساخت جدول‌ها
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 2. روشن کردن Consumer موقع بالا آمدن برنامه
@app.on_event("startup")
def startup_event():
    start_consumer_thread()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "Payment Service is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# 3. این همان تابعی است که جا مانده بود!
@app.get("/api/v1/payments/{payment_id}")
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    # الف) اول سعی کن با شناسه سفارش (UUID) پیدا کنی
    # (چون ممکن است تست با UUID درخواست بدهد)
    payment = db.query(Payment).filter(Payment.order_id == payment_id).first()

    # ب) اگر پیدا نشد و ورودی عدد بود (مثل 4)، با ID اصلی دیتابیس بگرد
    if not payment and payment_id.isdigit():
        payment = db.query(Payment).filter(Payment.id == int(payment_id)).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "status": payment.status,
        "is_successful": payment.is_successful
    }