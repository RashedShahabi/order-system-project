import json
import pika
import threading
import time
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Payment

class PaymentConsumer:
    def __init__(self):
        while True:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host='rabbitmq', heartbeat=600, blocked_connection_timeout=300))
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)
                
                result = self.channel.queue_declare(queue='', exclusive=True)
                queue_name = result.method.queue
                
                # گوش دادن به رزرو موفق (عادی)
                self.channel.queue_bind(exchange='events', queue=queue_name, routing_key='stock.reserved')
                
                # --- تغییر مهم: گوش دادن به شکست موجودی (برای هماهنگی ID ها) ---
                self.channel.queue_bind(exchange='events', queue=queue_name, routing_key='stock.rejected')
                
                self.channel.basic_consume(queue=queue_name, on_message_callback=self.callback, auto_ack=True)
                print(" [*] Payment Service listening...")
                self.channel.start_consuming()
                break
            except Exception as e:
                time.sleep(5)

    def callback(self, ch, method, properties, body):
        db = SessionLocal()
        try:
            event = json.loads(body)
            print(f" [x] Payment Processing: {method.routing_key} -> {event}")
            
            order_id = event.get("order_id")
            
            # --- سناریوی ۲: اگر انبار رد کرد، یک رکورد خالی بساز تا ID هماهنگ بماند ---
            if method.routing_key == 'stock.rejected':
                dummy_payment = Payment(
                    order_id=order_id,
                    amount=0,
                    currency="USD",
                    status="FAILED",
                    is_successful=False
                )
                db.add(dummy_payment)
                db.commit()
                print(f"Dummy payment created for {order_id} to sync IDs.")
                return 
            # -------------------------------------------------------------------

            # --- سناریوی ۱ و ۳: پردازش عادی ---
            amount = event.get("amount", 0)
            item_sku = event.get("item_sku")
            quantity = event.get("quantity")
            
            if amount > 200:
                routing_key = "payment.failed"
                db_status = "FAILED"
                is_success = False
            else:
                routing_key = "payment.succeeded"
                db_status = "SUCCESS"
                is_success = True

            new_payment = Payment(
                order_id=order_id,
                amount=amount,
                currency="USD",
                status=db_status,
                is_successful=is_success
            )
            db.add(new_payment)
            db.commit()
            print(f"Payment saved: {db_status}")

            payload = {
                "order_id": order_id, 
                "status": routing_key,
                "item_sku": item_sku,
                "quantity": quantity
            }
            
            self.channel.basic_publish(
                exchange='events',
                routing_key=routing_key,
                body=json.dumps(payload)
            )
        except Exception as e:
            print(f"Error: {e}")
        finally:
            db.close()

def start_consumer_thread():
    t = threading.Thread(target=PaymentConsumer, daemon=True)
    t.start()