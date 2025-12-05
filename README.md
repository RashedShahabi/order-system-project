# Order Management System (Microservices)
This project is an implementation of an Order Management System using a Microservices Architecture. It consists of three independent services: Inventory, Payment, and Order Service.

## Architecture

The system follows a microservices architecture where each service has its own database (Database-per-Service pattern).

*   **Inventory Service**: Manages product stock (Reserve/Release).
*   **Payment Service**: Simulates payment authorization.
*   **Order Service**: Coordinates the order lifecycle and handles idempotency.

## Tech Stack

*   **Language**: Python 3.x
*   **Framework**: FastAPI
*   **Database**: PostgreSQL
*   **Infrastructure**: Docker & Docker Compose

## How to Run

1.  **Clone the repository**.

2.  **Start the services** using Docker Compose:

        docker-compose up --build -d

3.  **Check status**: Ensure all 6 containers (3 apps + 3 databases) are running:

        docker ps

4.  **Stop the services**:

        docker-compose down

## API Documentation (Swagger UI)

Once running, you can access the interactive API docs at:

*   **Order Service**: [http://localhost:8001/docs](http://localhost:8001/docs)
*   **Inventory Service**: [http://localhost:8002/docs](http://localhost:8002/docs)
*   **Payment Service**: [http://localhost:8003/docs](http://localhost:8003/docs)


## Endpoints Overview

### 1. Inventory Service (Port 8002)
*   `POST /api/v1/stock/items`: Add or update items.
*   `POST /api/v1/stock/reserve`: Reserve stock (Internal use).
*   `POST /api/v1/stock/release`: Release stock (Internal use).
*   `GET /api/v1/stock/{sku}`: Check stock level.


### 2. Payment Service (Port 8003)
*   `POST /api/v1/payments/authorize`: Mock payment authorization.
*   Amount < 1000: **Authorized**
*   Amount >= 1000: **Declined**


### 3. Order Service (Port 8001)
*   `POST /api/v1/orders`: Create a new order.
*   Requires: `item_sku`, `quantity`, `amount`, `idempotency_key`.

## Testing Scenarios

**Scenario 1: Successful Order**
1.  Add Item (Inventory): `POST /items` -> `{ "item_sku": "A", "quantity": 10 }`
2.  Place Order (Order): `POST /orders` -> `{ "item_sku": "A", "quantity": 2, "amount": 100, "idempotency_key": "key-1" }`
3.  Result: Order `CONFIRMED`, Stock becomes `8`.

**Scenario 2: Payment Failure**
1.  Place Order (Order): `POST /orders` -> `{ "item_sku": "A", "quantity": 1, "amount": 1500, "idempotency_key": "key-2" }`
2.  Result: Order `FAILED` (Payment declined), Stock remains `8`.

**Scenario 3: Insufficient Stock**
1.  Place Order (Order): `POST /orders` -> `{ "item_sku": "A", "quantity": 20, "amount": 100, "idempotency_key": "key-3" }`
2.  Result: Order `FAILED`, Stock remains `8`.

**Scenario 4: Idempotency**
1.  Send the same request from Scenario 1 again with the same `idempotency_key` ("key-1").
2.  Result: Returns the **existing** order details. No new order created, stock is not reduced again.
















