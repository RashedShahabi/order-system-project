import json
import pika
import os
import time
import threading
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import StockItem
from .messaging.bus import RabbitMQProducer

class InventoryConsumer:
    def __init__(self):
        self.producer = RabbitMQProducer()
        self.host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.connection = None
        self.channel = None

    def connect(self):
        """Connects to RabbitMQ and sets up queues/exchanges."""
        while True:
            try:
                credentials = pika.PlainCredentials('guest', 'guest')
                parameters = pika.ConnectionParameters(self.host, credentials=credentials)
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare the exchange (ensure it exists)
                self.channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)

                # --- Queue 1: Handle New Orders ---
                # Listen for 'order.created'
                self.channel.queue_declare(queue='inventory.order.created', durable=True)
                self.channel.queue_bind(
                    exchange='events', queue='inventory.order.created', routing_key='order.created'
                )

                # --- Queue 2: Handle Failed Payments (Compensation) ---
                # Listen for 'payment.failed'
                self.channel.queue_declare(queue='inventory.payment.failed', durable=True)
                self.channel.queue_bind(
                    exchange='events', queue='inventory.payment.failed', routing_key='payment.failed'
                )

                print("Inventory Consumer connected to RabbitMQ!")
                break
            except pika.exceptions.AMQPConnectionError:
                print("RabbitMQ not ready, retrying in 5 seconds...")
                time.sleep(5)

    def process_order_created(self, ch, method, properties, body):
        """
        Received 'order.created'. 
        Action: Check stock -> Reserve OR Reject.
        """
        data = json.loads(body)
        print(f" [x] Received Order: {data}")
        
        db = SessionLocal()
        try:
            item = db.query(StockItem).filter(StockItem.item_sku == data['item_sku']).first()
            
            # Logic: If item exists AND we have enough quantity
            if item and item.quantity >= data['quantity']:
                # Reserve Stock
                item.quantity -= data['quantity']
                db.commit()
                print(f"Stock reserved for Order {data['order_id']}")
                
                # Publish Success Event
                event_data = data.copy() # Copy order data
                self.producer.publish(routing_key="stock.reserved", message=event_data)
                
            else:
                # Stock Insufficient
                print(f"Stock insufficient for Order {data['order_id']}")
                
                # Publish Failure Event
                failure_data = {
                    "order_id": data["order_id"],
                    "reason": "INSUFFICIENT_STOCK"
                }
                self.producer.publish(routing_key="stock.rejected", message=failure_data)
                
        except Exception as e:
            print(f"Error processing order: {e}")
        finally:
            db.close()
            # Acknowledge the message so RabbitMQ removes it from queue
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def process_payment_failed(self, ch, method, properties, body):
        """
        Received 'payment.failed'.
        Action: Rollback (Release) the reserved stock.
        """
        data = json.loads(body)
        print(f" [x] Payment Failed for Order {data.get('order_id')}. Rolling back stock...")
        
        db = SessionLocal()
        try:
            # We assume the payload contains item_sku and quantity to release
            # If strictly following Phase 2 PDF, payment.failed might only have order_id.
            # But for simplicity, we assume we passed item info along or fetched it.
            # NOTE: To be robust, we assume data has 'item_sku' and 'quantity'.
            
            if 'item_sku' in data and 'quantity' in data:
                item = db.query(StockItem).filter(StockItem.item_sku == data['item_sku']).first()
                if item:
                    item.quantity += data['quantity']
                    db.commit()
                    print(f"Stock released/restored for Order {data['order_id']}")
            else:
                print("Warning: Missing item info in payment.failed event, cannot restore stock.")

        except Exception as e:
            print(f"Error processing rollback: {e}")
        finally:
            db.close()
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_listening(self):
        """Starts the consuming loop."""
        if not self.connection:
            self.connect()

        # Tell RabbitMQ which functions to call when messages arrive
        self.channel.basic_consume(
            queue='inventory.order.created', on_message_callback=self.process_order_created
        )
        self.channel.basic_consume(
            queue='inventory.payment.failed', on_message_callback=self.process_payment_failed
        )

        print(" [*] Inventory Service waiting for events...")
        self.channel.start_consuming()

def start_consumer_thread():
    """Helper to run consumer in a background thread."""
    consumer = InventoryConsumer()
    thread = threading.Thread(target=consumer.start_listening, daemon=True)
    thread.start()