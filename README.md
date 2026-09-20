
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

Rohan S