# Phase 2: Event-Driven Order System with RabbitMQ

This project implements an Event-Driven Architecture for an Order Management System using **FastAPI**, **RabbitMQ**, and **PostgreSQL**.

## 🚀 Features Implemented
1.  **Event-Driven Communication:** Replaced synchronous HTTP calls with asynchronous RabbitMQ messaging using `pika`.
2.  **Saga Pattern (Choreography):**
    -   **Order Service:** Publishes `order.created`.
    -   **Inventory Service:** Consumes order events, reserves stock, and publishes `stock.reserved` or `stock.rejected`.
    -   **Payment Service:** Consumes `stock.reserved`, processes payment, and publishes `payment.succeeded` or `payment.failed`.
    -   **Compensation Logic:** If payment fails (amount >= 1000), Inventory Service listens to `payment.failed` and restores the stock.
3.  **Database Integration:** Added a PostgreSQL database for the Payment Service to store transaction records.
4.  **Idempotency:** Handled duplicate requests in Order Service to prevent double-booking.

## 🛠️ How to Run
1.  **Start the services:**
    ```bash
    docker-compose up --build -d
    ```
2.  **Access Swagger UI:**
    -   Order Service: [http://localhost:8001/docs](http://localhost:8001/docs)
    -   Inventory Service: [http://localhost:8002/docs](http://localhost:8002/docs)
    -   Payment Service: [http://localhost:8003/docs](http://localhost:8003/docs)

## 🧪 Tested Scenarios
1.  **Happy Path:** Order created -> Stock reserved -> Payment succeeded -> Order confirmed.
2.  **Insufficient Stock:** Order created -> Stock insufficient -> Order rejected.
3.  **Compensation (Saga):** Order created -> Stock reserved -> Payment failed (Amount > 1000) -> Stock restored (Compensated).