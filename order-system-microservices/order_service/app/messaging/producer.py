import pika
import json

class RabbitMQProducer:
    def __init__(self):
        # اتصال به RabbitMQ با تنظیمات پایدار
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbitmq', 
                heartbeat=600, 
                blocked_connection_timeout=300
            )
        )
        self.channel = self.connection.channel()
        # تعریف Exchange (محل تبادل پیام)
        self.channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)

    def publish_event(self, event_data: dict, routing_key: str = "order.created"):
        try:
            self.channel.basic_publish(
                exchange='events',
                routing_key=routing_key,
                body=json.dumps(event_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # ذخیره پیام روی دیسک (Persistent)
                )
            )
            print(f" [x] Sent event '{routing_key}': {event_data}")
        except Exception as e:
            print(f"Failed to publish message: {e}")
            raise e
        finally:
            self.connection.close()