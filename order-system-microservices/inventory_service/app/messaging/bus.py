import pika
import json
import os
import time

class RabbitMQProducer:
    """
    Handles the connection to RabbitMQ and publishing of events.
    This class is designed to be resilient, retrying connections if RabbitMQ is not ready.
    """

    def __init__(self, exchange_name="events", exchange_type="topic"):
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.connection = None
        self.channel = None
        # Automatically connect upon initialization
        self.connect()

    def connect(self):
        """Establishes a connection to RabbitMQ with retry logic."""
        while True:
            try:
                # Get RabbitMQ host from environment variables (default: rabbitmq)
                host = os.getenv("RABBITMQ_HOST", "rabbitmq")
                credentials = pika.PlainCredentials('guest', 'guest')
                parameters = pika.ConnectionParameters(host=host, credentials=credentials)
                
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                
                # Declare the exchange (durable ensures it survives restarts)
                self.channel.exchange_declare(
                    exchange=self.exchange_name, 
                    exchange_type=self.exchange_type, 
                    durable=True
                )
                print(f"Successfully connected to RabbitMQ Exchange: {self.exchange_name}")
                break
            except pika.exceptions.AMQPConnectionError:
                # Wait and retry if RabbitMQ is not yet fully booted (common in Docker Compose)
                print("RabbitMQ not ready yet, retrying in 5 seconds...")
                time.sleep(5)

    def publish(self, routing_key, message):
        """
        Publishes a message to the exchange with a specific routing key.
        
        Args:
            routing_key (str): The topic key (e.g., 'order.created', 'stock.reserved').
            message (dict): The data payload to send.
        """
        # Reconnect if the connection was lost
        if not self.connection or self.connection.is_closed:
            self.connect()
        
        try:
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            print(f" [x] Sent event '{routing_key}': {message}")
        except Exception as e:
            print(f"Failed to publish message: {e}")

    def close(self):
        """Closes the connection cleanly."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()