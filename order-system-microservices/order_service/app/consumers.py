# File: order_service/app/consumers.py

import json
import pika
import threading
import time
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Order  # <--- دقت کنید: اینجا Order است، نه StockItem

class OrderConsumer:
    def __init__(self):
        # تلاش برای اتصال تا زمانی که RabbitMQ آماده شود
        while True:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host='rabbitmq', heartbeat=600, blocked_connection_timeout=300))
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)
                
                # صف اختصاصی برای شنیدن نتیجه نهایی
                result = self.channel.queue_declare(queue='', exclusive=True)
                queue_name = result.method.queue

                # گوش دادن به پیام‌های موفقیت یا شکست نهایی
                self.channel.queue_bind(exchange='events', queue=queue_name, routing_key='payment.succeeded')
                self.channel.queue_bind(exchange='events', queue=queue_name, routing_key='stock.rejected')
                self.channel.queue_bind(exchange='events', queue=queue_name, routing_key='payment.failed')

                self.channel.basic_consume(queue=queue_name, on_message_callback=self.callback, auto_ack=True)
                print(" [*] Order Consumer started listening...")
                self.channel.start_consuming()
                break
            except Exception as e:
                print(f"Connection failed, retrying in 5s: {e}")
                time.sleep(5)

    def callback(self, ch, method, properties, body):
        try:
            event = json.loads(body)
            routing_key = method.routing_key
            print(f" [x] Order Service Received: {routing_key} -> {event}")
            
            order_id = event.get("order_id")
            if not order_id:
                return

            db = SessionLocal()
            order = db.query(Order).filter(Order.order_id == order_id).first()
            
            if order:
                # آپدیت وضعیت سفارش بر اساس پیام دریافتی
                if routing_key == "payment.succeeded":
                    order.status = "COMPLETED"
                elif routing_key == "stock.rejected":
                    order.status = "CANCELLED_NO_STOCK"
                elif routing_key == "payment.failed":
                    order.status = "CANCELLED_PAYMENT_FAILED"
                
                db.commit()
                print(f"Order {order_id} updated to {order.status}")
            db.close()

        except Exception as e:
            print(f"Error processing event: {e}")

def start_consumer_thread():
    t = threading.Thread(target=OrderConsumer, daemon=True)
    t.start()