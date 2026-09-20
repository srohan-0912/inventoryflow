
# InventoryFlow — Multi-Tenant Inventory & Order Management Platform

InventoryFlow is a backend application for managing products, warehouses, inventory, customers, and orders with organization-level data isolation.

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, SQLAlchemy
- **Migrations:** Alembic
- **Caching:** Redis
- **Authentication:** JWT, role-based access control (RBAC)
- **Testing:** Pytest
- **Containerization:** Docker, Docker Compose
- **API Documentation:** OpenAPI / Swagger UI

## Features

- JWT-based authentication
- Role-based access control
- Organization-level tenant isolation
- Product, warehouse, and customer management
- Inventory adjustments and movement tracking
- Order creation and status workflows
- Redis-based product caching
- Request logging and structured error responses
- Automated tests

## Project Structure

```text
inventoryflow/
├── alembic/
│   └── versions/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── main.py
├── tests/
├── .env.example
├── .gitignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/srohan-0912/inventoryflow.git
cd inventoryflow
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. Configure the required database and JWT settings using your own local values.

Do not commit `.env` or expose credentials.

### 5. Run database migrations

```powershell
alembic upgrade head
```

### 6. Start the API

```powershell
uvicorn app.main:app --reload
```

Open:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Run with Docker

With Docker Desktop running, use:

```powershell
docker compose up --build
```

To stop the containers:

```powershell
docker compose down
```

## Run Tests

```powershell
pytest
```

## Project Status

Core backend workflows, authentication, inventory and order operations, automated tests, Docker setup, Redis caching, and request logging have been implemented and tested during development.

**Deployment:** AWS deployment is not yet completed.

## Future Improvements

- Complete deployment and production configuration
- Expand API documentation and usage examples
- Add further integration and performance tests

## Author


## API Endpoints

Base URL: `http://127.0.0.1:8000`

Interactive API documentation is available at `/docs`.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Log in and obtain a token |

### Organizations

| Method | Endpoint | Description |
|---|---|---|
| GET | `/organizations/` | List organizations |
| POST | `/organizations/` | Create an organization |

### Products

| Method | Endpoint | Description |
|---|---|---|
| POST | `/products/` | Create a product |
| GET | `/products/` | List products |
| GET | `/products/{product_id}` | Get a product |
| PUT | `/products/{product_id}` | Update a product |
| DELETE | `/products/{product_id}` | Delete a product |

### Warehouses

| Method | Endpoint | Description |
|---|---|---|
| POST | `/warehouses/` | Create a warehouse |
| GET | `/warehouses/` | List warehouses |
| GET | `/warehouses/{warehouse_id}` | Get a warehouse |
| PUT | `/warehouses/{warehouse_id}` | Update a warehouse |
| DELETE | `/warehouses/{warehouse_id}` | Delete a warehouse |

### Customers

| Method | Endpoint | Description |
|---|---|---|
| POST | `/customers/` | Create a customer |
| GET | `/customers/` | List customers |
| GET | `/customers/{customer_id}` | Get a customer |
| PUT | `/customers/{customer_id}` | Update a customer |
| DELETE | `/customers/{customer_id}` | Delete a customer |

### Inventory

| Method | Endpoint | Description |
|---|---|---|
| POST | `/inventory/` | Create an inventory record |
| GET | `/inventory/` | List inventory |
| GET | `/inventory/{inventory_id}` | Get an inventory record |
| PUT | `/inventory/{inventory_id}` | Update an inventory record |
| PATCH | `/inventory/{inventory_id}/adjust` | Adjust inventory |
| DELETE | `/inventory/{inventory_id}` | Delete an inventory record |

### Inventory Movements

| Method | Endpoint | Description |
|---|---|---|
| GET | `/inventory-movements/` | List inventory movements |
| GET | `/inventory-movements/{movement_id}` | Get a movement |

### Orders

| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders/` | Create an order |
| GET | `/orders/` | List orders |
| GET | `/orders/{order_id}` | Get an order |
| POST | `/orders/{order_id}/confirm` | Confirm an order |
| POST | `/orders/{order_id}/cancel` | Cancel an order |
| POST | `/orders/{order_id}/ship` | Ship an order |
| POST | `/orders/{order_id}/complete` | Complete an order |


## Authentication Example

InventoryFlow uses JWT bearer tokens for authenticated API requests.

### 1. Register a user

Send a `POST` request to `/auth/register`.

```json
{
  "organization_id": 1,
  "name": "Demo User",
  "email": "demo@example.com",
  "password": "DemoPassword123"
}
```

The password must contain between 8 and 72 characters.

A successful registration returns the user details, including the assigned role and account status. Newly registered users receive the `STAFF` role.

### 2. Log in

Send a `POST` request to `/auth/login`.

```json
{
  "email": "demo@example.com",
  "password": "DemoPassword123"
}
```

A successful login returns:

```json
{
  "access_token": "<your_access_token>",
  "token_type": "bearer"
}
```

### 3. Use the access token

For protected endpoints, include the token in the HTTP `Authorization` header:

```http
Authorization: Bearer <your_access_token>
```

In Swagger UI (`/docs`), use the **Authorize** button if available and enter the bearer token as prompted.

**Note:** Replace the example organization ID with an organization that exists in your database. Use a unique email address for each registration.


## Product API Examples

All product endpoints require authentication and operate within the authenticated user's organization.

### 1. Create a product

Send a `POST` request to `/products/`.

```json
{
  "sku": "DEMO-001",
  "name": "Demo Laptop",
  "description": "Laptop for demonstration",
  "price": "55000.00",
  "is_active": true
}
```

The `sku` and `name` fields are required. The price must be zero or greater and supports up to two decimal places.

### 2. List products

Send a `GET` request to `/products/`.

Optional pagination parameters:

- `skip` — number of records to skip
- `limit` — number of records to return

Example:

```http
GET /products/?skip=0&limit=10
```

### 3. Get a product

```http
GET /products/1
```

Replace `1` with the product ID.

### 4. Update a product

Send a `PUT` request to `/products/{product_id}`.

```json
{
  "name": "Updated Demo Laptop",
  "price": "52000.00"
}
```

Only include the fields you want to update.

### 5. Delete a product

```http
DELETE /products/{product_id}
```

A successful deletion returns HTTP `204 No Content`.

## Inventory API Examples

### 1. Create inventory

**POST** `/inventory/`

```json
{
  "product_id": 1,
  "warehouse_id": 1,
  "quantity": 25,
  "reserved_quantity": 0
}
```

### 2. Adjust inventory quantity

**PATCH** `/inventory/{inventory_id}/adjust`

```json
{
  "quantity_change": 5
}
```

Use a positive value to increase stock or a negative value to decrease it.

### 3. Update inventory

**PUT** `/inventory/{inventory_id}`

```json
{
  "quantity": 30,
  "reserved_quantity": 0
}
```

### 4. Retrieve inventory

* `GET /inventory/` — List inventory records.
* `GET /inventory/{inventory_id}` — Retrieve a specific inventory record.
* `DELETE /inventory/{inventory_id}` — Delete an inventory record.

---

## Order API Examples

### 1. Create an order

**POST** `/orders/`

```json
{
  "customer_id": 1,
  "warehouse_id": 1,
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```

Each order must contain at least one item. A product can appear only once in an order.

### 2. Order lifecycle endpoints

| Action            | Endpoint                           |
| ----------------- | ---------------------------------- |
| List orders       | `GET /orders/`                     |
| Retrieve an order | `GET /orders/{order_id}`           |
| Confirm an order  | `POST /orders/{order_id}/confirm`  |
| Cancel an order   | `POST /orders/{order_id}/cancel`   |
| Ship an order     | `POST /orders/{order_id}/ship`     |
| Complete an order | `POST /orders/{order_id}/complete` |

### 3. Order workflow

1. Create an order with a customer, warehouse, and products.
2. Confirm the order to reserve the required inventory.
3. Cancel the order if it should not proceed.
4. Ship the confirmed order to decrease inventory quantity.
5. Complete the order after fulfillment.

**Example:** In local testing, an order for 2 units was confirmed and shipped. Inventory quantity decreased from 30 to 28, and reserved quantity returned to 0.

---

## Inventory Movement API

* `GET /inventory-movements/` — List inventory movements.
* `GET /inventory-movements/{movement_id}` — Retrieve a specific inventory movement.

## Database Design

InventoryFlow uses PostgreSQL and SQLAlchemy ORM to manage organization-based inventory and order data.

### Database Tables

| Table | Purpose | Key Fields |
|---|---|---|
| `organizations` | Stores organizations | `id`, `name`, `created_at`, `updated_at` |
| `users` | Stores users and roles | `id`, `organization_id`, `name`, `email`, `password_hash`, `role`, `is_active` |
| `products` | Stores product details | `id`, `organization_id`, `sku`, `name`, `price`, `is_active` |
| `warehouses` | Stores warehouse information | `id`, `organization_id`, `name`, `location` |
| `customers` | Stores customer contact information | `id`, `organization_id`, `name`, `email`, `phone`, `address` |
| `inventory` | Tracks product quantities by warehouse | `id`, `organization_id`, `product_id`, `warehouse_id`, `quantity`, `reserved_quantity` |
| `orders` | Stores customer orders and status | `id`, `organization_id`, `customer_id`, `warehouse_id`, `status`, `total_amount` |
| `order_items` | Stores products and quantities in orders | `id`, `order_id`, `product_id`, `quantity`, `unit_price`, `subtotal` |
| `inventory_movements` | Records inventory movement details | `id`, `organization_id`, `product_id`, `warehouse_id`, `order_id`, `movement_type`, `quantity` |

### Entity Relationships

- An organization has multiple users, products, warehouses, customers, inventory records, and orders.
- A product can have inventory records across multiple warehouses.
- A warehouse can contain inventory for multiple products.
- A customer can have multiple orders.
- An order belongs to a customer and a warehouse, and contains order items.
- Each order item references a product.
- Inventory movements reference an organization, product, and warehouse, and can optionally reference an order.

### Data Integrity

- Product SKUs are unique within an organization.
- Warehouse names are unique within an organization.
- An inventory record is unique for each organization, product, and warehouse combination.
- Inventory quantity and reserved quantity cannot be negative.
- Reserved quantity cannot exceed total quantity.
- Order item quantities must be greater than zero.
- Order totals, item prices, and subtotals cannot be negative.

### User Roles

- `OWNER`
- `ADMIN`
- `MANAGER`
- `STAFF`

### Order Statuses

`PENDING`, `CONFIRMED`, `CANCELLED`, `SHIPPED`, `COMPLETED`

### Inventory Movement Types

`PURCHASE`, `SALE`, `ADJUSTMENT`, `TRANSFER_IN`, `TRANSFER_OUT`, `RETURN`

## Database Relationship Diagram

The following diagram shows the main relationships between InventoryFlow database tables.

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : has
    ORGANIZATIONS ||--o{ PRODUCTS : owns
    ORGANIZATIONS ||--o{ WAREHOUSES : owns
    ORGANIZATIONS ||--o{ CUSTOMERS : manages
    ORGANIZATIONS ||--o{ INVENTORY : tracks
    ORGANIZATIONS ||--o{ ORDERS : manages
    ORGANIZATIONS ||--o{ INVENTORY_MOVEMENTS : records

    PRODUCTS ||--o{ INVENTORY : stocked_in
    WAREHOUSES ||--o{ INVENTORY : contains

    CUSTOMERS ||--o{ ORDERS : places
    WAREHOUSES ||--o{ ORDERS : fulfills

    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : references

    PRODUCTS ||--o{ INVENTORY_MOVEMENTS : tracks
    WAREHOUSES ||--o{ INVENTORY_MOVEMENTS : records
    ORDERS o|--o{ INVENTORY_MOVEMENTS : generates


## System Architecture

InventoryFlow follows a layered backend architecture to separate API handling, business logic, database operations, and supporting services.

```mermaid
flowchart TD
    A[Client / API Consumer] --> B[FastAPI Application]

    B --> C[Authentication & RBAC]
    C --> D[API Routes]

    D --> E[Business Logic]
    E --> F[SQLAlchemy ORM]

    F --> G[(PostgreSQL Database)]
    E --> H[(Redis Cache)]

    I[Alembic Migrations] --> G
    J[Pytest] --> B
    K[Docker Compose] -. runs .-> B
    K -. runs .-> G
    K -. runs .-> H

## Limitations and Future Improvements

### Current Limitations

- AWS deployment is not completed; the application currently runs locally using Docker Compose.
- Redis caching is currently implemented for product API responses.
- Automated tests cover core API functionality and business workflows, but broader performance and load testing is still needed.

### Future Improvements

- Deploy the application to AWS with secure configuration and monitoring.
- Add CI/CD deployment automation.
- Implement more comprehensive cache invalidation and monitoring.
- Add performance and load testing for high-traffic scenarios.
- Improve observability with metrics, dashboards, and centralized logs.
- Add more advanced inventory reporting and analytics.



## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/srohan-0912/inventoryflow.git
cd inventoryflow
```

### 2. Create and activate a virtual environment

For Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root.

Use `.env.example` as a reference and configure your own local database and JWT settings.

Example `.env.example`:

```dotenv
DATABASE_URL=postgresql+psycopg://username:password@localhost:5433/inventoryflow
JWT_SECRET_KEY=replace_with_a_secure_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=redis://localhost:6379/0
```

Use your own database credentials and a secure random JWT secret.

**Important:** Do not commit `.env` or expose credentials.

### 5. Run database migrations

Make sure PostgreSQL is running and the database is configured correctly.

```powershell
alembic upgrade head
```

### 6. Start the API

```powershell
uvicorn app.main:app --reload
```

Open these URLs:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Run with Docker

Make sure Docker Desktop is running.

### 1. Start the services

```powershell
docker compose up --build
```

This starts the API, PostgreSQL, and Redis services.

### 2. Run database migrations

Open another terminal in the project directory:

```powershell
docker compose exec api alembic upgrade head
```

### 3. Access the application

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### 4. Stop the containers

```powershell
docker compose down
```

This stops and removes the containers while retaining named volumes.

**Note:** Do not use `docker compose down -v` unless you intentionally want to delete the volumes and their stored data.

## Run Tests

Activate your virtual environment and run:

```powershell
python -m pytest
```

The latest reported test run completed with 106 passing tests. Run the command above to verify the current checkout.

## Project Status

Core backend workflows, authentication, inventory and order operations, automated tests, Docker setup, Redis caching, and request logging have been implemented and tested during development.

**Deployment:** AWS deployment is not yet completed.

---

## API Endpoints

Base URL:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Authenticate and receive an access token |

### Organizations

| Method | Endpoint | Description |
|---|---|---|
| POST | `/organizations/` | Create an organization |
| GET | `/organizations/me` | Get the current user's organization |

### Products

| Method | Endpoint | Description |
|---|---|---|
| POST | `/products/` | Create a product |
| GET | `/products/` | List products |
| GET | `/products/{product_id}` | Get product details |
| PUT | `/products/{product_id}` | Update a product |
| DELETE | `/products/{product_id}` | Delete a product |

### Warehouses

| Method | Endpoint | Description |
|---|---|---|
| POST | `/warehouses/` | Create a warehouse |
| GET | `/warehouses/` | List warehouses |
| GET | `/warehouses/{warehouse_id}` | Get warehouse details |
| PUT | `/warehouses/{warehouse_id}` | Update a warehouse |
| DELETE | `/warehouses/{warehouse_id}` | Delete a warehouse |

### Customers

| Method | Endpoint | Description |
|---|---|---|
| POST | `/customers/` | Create a customer |
| GET | `/customers/` | List customers |
| GET | `/customers/{customer_id}` | Get customer details |
| PUT | `/customers/{customer_id}` | Update a customer |
| DELETE | `/customers/{customer_id}` | Delete a customer |

### Inventory

| Method | Endpoint | Description |
|---|---|---|
| POST | `/inventory/` | Create an inventory record |
| GET | `/inventory/` | List inventory |
| GET | `/inventory/{inventory_id}` | Get inventory details |
| PUT | `/inventory/{inventory_id}` | Update inventory |
| POST | `/inventory/{inventory_id}/adjust` | Adjust stock quantity |

### Orders

| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders/` | Create an order |
| GET | `/orders/` | List orders |
| GET | `/orders/{order_id}` | Get order details |
| POST | `/orders/{order_id}/confirm` | Confirm an order |
| POST | `/orders/{order_id}/ship` | Ship an order |
| POST | `/orders/{order_id}/complete` | Complete an order |
| POST | `/orders/{order_id}/cancel` | Cancel an order |

### Inventory Movements

| Method | Endpoint | Description |
|---|---|---|
| GET | `/inventory-movements/` | List inventory movement records |

> Endpoint availability and request/response schemas can be inspected in the interactive Swagger UI at `/docs`.

---

## Authentication

InventoryFlow uses JWT-based authentication to protect API endpoints.

### 1. Register a user

Send a `POST` request to:

```text
/auth/register
```

Example request body:

```json
{
  "organization_id": 1,
  "name": "Demo User",
  "email": "demo@example.com",
  "password": "DemoPassword123"
}
```

Use an existing organization ID and an email address that has not already been registered.

### 2. Log in

Send a `POST` request to:

```text
/auth/login
```

Provide the login credentials using the request format shown in Swagger.

The login endpoint returns an access token when authentication succeeds.

### 3. Authorize requests

For protected endpoints, include the JWT access token in the request header:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

In Swagger UI:

1. Open `/docs`.
2. Select **Authorize**.
3. Enter your access token using the format expected by the authorization dialog.
4. Execute the protected endpoint.

Never commit real access tokens, passwords, or secret keys to GitHub.

---

---

## Product API Examples

These examples demonstrate common product operations. Use a valid JWT access token and an organization that exists in your database.

### Create a product

**Endpoint:** `POST /products/`

Example request body:

```json
{
  "name": "Dell Laptop",
  "sku": "DEMO-001",
  "description": "Business laptop",
  "price": 55000,
  "is_active": true
}
```

Include any additional required fields shown in Swagger for your current schema.

### List products

**Endpoint:** `GET /products/`

Retrieve products belonging to the authenticated user's organization.

The endpoint supports pagination and filtering where configured.

### Get product details

**Endpoint:** `GET /products/{product_id}`

Replace `{product_id}` with the ID of the product you want to retrieve.

### Update a product

**Endpoint:** `PUT /products/{product_id}`

Example request body:

```json
{
  "name": "Dell Laptop Updated",
  "description": "Updated business laptop details",
  "price": 58000,
  "is_active": true
}
```

Check the request schema in Swagger and provide all required fields.

### Delete a product

**Endpoint:** `DELETE /products/{product_id}`

Deletes the selected product when the request is authorized and the operation is permitted.

---

## Inventory and Order Workflow

InventoryFlow supports inventory adjustments and an order lifecycle.

A typical workflow is:

1. Create a product.
2. Create a warehouse.
3. Create an inventory record linking the product and warehouse.
4. Create a customer.
5. Create an order for that customer.
6. Confirm the order.
7. Ship the order.
8. Complete the order.

### Inventory adjustment

Use:

```text
POST /inventory/{inventory_id}/adjust
```

This endpoint adjusts the stock quantity for an inventory record. Check the API schema for the required adjustment fields.

### Order lifecycle

The order workflow includes these operations:

| Action | Endpoint |
|---|---|
| Create an order | `POST /orders/` |
| Confirm an order | `POST /orders/{order_id}/confirm` |
| Ship an order | `POST /orders/{order_id}/ship` |
| Complete an order | `POST /orders/{order_id}/complete` |
| Cancel an order | `POST /orders/{order_id}/cancel` |

The application tracks inventory changes through the order workflow and records inventory movements.

> Use the IDs returned by your own API requests. The exact request bodies and allowed state transitions are documented in Swagger.

---

---

## Database Design

InventoryFlow uses PostgreSQL as its relational database.

The database is designed to support organization-level data isolation, inventory management, and order processing.

### Main entities

| Entity | Purpose |
|---|---|
| Organizations | Represents tenant organizations |
| Users | Stores user accounts and access roles |
| Products | Stores product details and SKU information |
| Warehouses | Stores warehouse information |
| Customers | Stores customer details |
| Inventory | Tracks product stock by warehouse |
| Orders | Stores customer orders and their statuses |
| Order Items | Stores products and quantities associated with orders |
| Inventory Movements | Records stock changes and their movement types |

### Entity Relationship Diagram

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : contains
    ORGANIZATIONS ||--o{ PRODUCTS : owns
    ORGANIZATIONS ||--o{ WAREHOUSES : owns
    ORGANIZATIONS ||--o{ CUSTOMERS : owns
    ORGANIZATIONS ||--o{ ORDERS : owns

    PRODUCTS ||--o{ INVENTORY : tracked_in
    WAREHOUSES ||--o{ INVENTORY : stores

    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : referenced_by

    INVENTORY ||--o{ INVENTORY_MOVEMENTS : records
```

---

## System Architecture

The application follows a backend API architecture built around FastAPI and PostgreSQL.

```mermaid
flowchart TD
    Client[Client / API Consumer] --> API[FastAPI Application]

    API --> Auth[JWT Authentication]
    Auth --> RBAC[Role-Based Access Control]

    RBAC --> Routes[API Routes]
    Routes --> Services[Business Logic]
    Services --> DB[(PostgreSQL)]
    Services --> Cache[(Redis)]

    DB --> Models[SQLAlchemy Models]
    Models --> Migrations[Alembic Migrations]

    API --> Tests[Pytest Tests]
    API --> Docs[OpenAPI / Swagger]
```

---

---

## Limitations

The current implementation is a portfolio project focused on backend development and core inventory and order management workflows.

The following areas may require further development before production use:

- Production deployment and infrastructure configuration.
- Automated database backups and recovery procedures.
- More comprehensive monitoring and observability.
- Additional security hardening and performance testing.
- Broader integration and load testing.

## Future Improvements

Potential future enhancements include:

- Deploying the application to a cloud environment.
- Adding a CI/CD deployment pipeline.
- Improving monitoring, logging, and alerting.
- Expanding automated test coverage.
- Adding advanced inventory analytics and reporting.
- Implementing more extensive operational and administrative features.

## Project Status

The core backend, database integration, authentication, role-based access control, inventory and order workflows, automated tests, Docker setup, and documentation have been developed.

**Cloud deployment is not yet completed.**

---

## Author

**Rohan S**

GitHub: [srohan-0912](https://github.com/srohan-0912)

Project Repository: [InventoryFlow](https://github.com/srohan-0912/inventoryflow)

---


Rohan S