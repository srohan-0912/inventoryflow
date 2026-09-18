
import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes.products import router as product_router
from app.api.routes.organizations import router as organization_router
from app.api.routes.warehouses import router as warehouse_router
from app.api.routes.customers import router as customer_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.orders import router as order_router
from app.api.routes.auth import router as auth_router
from app.api.routes.inventory_movements import (
    router as inventory_movement_router,
)


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger("inventoryflow")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="InventoryFlow",
    description="Multi-Tenant Inventory & Order Management Platform",
    version="1.0.0",
)


# ============================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        request.state.request_id = request_id

        try:
            response = await call_next(request)

            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            logger.info(
                "request_id=%s method=%s path=%s "
                "status_code=%s duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )

            response.headers["X-Request-ID"] = request_id

            return response

        except Exception:
            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            logger.exception(
                "request_id=%s method=%s path=%s "
                "duration_ms=%.2f request_failed=true",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )

            raise


app.add_middleware(RequestLoggingMiddleware)


# ============================================================
# REGISTER API ROUTERS
# ============================================================

app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(product_router)
app.include_router(warehouse_router)
app.include_router(customer_router)
app.include_router(inventory_router)
app.include_router(order_router)
app.include_router(inventory_movement_router)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "InventoryFlow API",
        "version": "1.0.0",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }