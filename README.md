
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
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── tests/
│   └── main.py
├── .env
├── .gitignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
└── README.md
```

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

Rohan S