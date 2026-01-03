import json
import pika
import os
import time
import threading
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Payment
from .messaging.bus import RabbitMQProducer

class PaymentConsumer:
    def __init__(self):
        self.producer = RabbitMQProducer()
        self.host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.connection = None
        self.channel = None

    def connect(self):
        """Connects to RabbitMQ."""
        while True:
            try:
                credentials = pika.PlainCredentials('guest', 'guest')
                parameters = pika.ConnectionParameters(self.host, credentials=credentials)
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare exchange
                self.channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)

                # --- Queue: Handle Stock Reserved ---
                # We only care if stock is successfully reserved.
                self.channel.queue_declare(queue='payment.stock.reserved', durable=True)
                self.channel.queue_bind(
                    exchange='events', queue='payment.stock.reserved', routing_key='stock.reserved'
                )

                print("Payment Consumer connected to RabbitMQ!")
                break
            except pika.exceptions.AMQPConnectionError:
                print("RabbitMQ not ready, retrying in 5 seconds...")
                time.sleep(5)

    def process_stock_reserved(self, ch, method, properties, body):
        """
        Received 'stock.reserved'.
        Action: Process Payment -> Publish Success/Failure.
        """
        data = json.loads(body)
        print(f" [x] Processing Payment for Order: {data}")
        
        db = SessionLocal()
        try:
            amount = data.get('amount', 0)
            order_id = data.get('order_id')
            
            # --- Business Logic ---
            # If amount < 1000 => Success
            # If amount >= 1000 => Fail
            is_successful = amount < 1000
            status = "success" if is_successful else "failed"
            
            # 1. Save to Database
            new_payment = Payment(
                order_id=order_id,
                amount=amount,
                currency=data.get('currency', 'USD'),
                status=status,
                is_successful=is_successful
            )
            db.add(new_payment)
            db.commit()
            print(f"Payment {status} for Order {order_id} saved to DB.")

            # 2. Publish Event
            if is_successful:
                routing_key = "payment.succeeded"
            else:
                routing_key = "payment.failed"
            
            # Send the event back to RabbitMQ so Order Service (and Inventory) can know
            self.producer.publish(routing_key=routing_key, message=data)

        except Exception as e:
            print(f"Error processing payment: {e}")
        finally:
            db.close()
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def start_listening(self):
        """Starts the consuming loop."""
        if not self.connection:
            self.connect()

        self.channel.basic_consume(
            queue='payment.stock.reserved', on_message_callback=self.process_stock_reserved
        )

        print(" [*] Payment Service waiting for events...")
        self.channel.start_consuming()

def start_consumer_thread():
    """Helper to run consumer in a background thread."""
    consumer = PaymentConsumer()
    thread = threading.Thread(target=consumer.start_listening, daemon=True)
    thread.start()