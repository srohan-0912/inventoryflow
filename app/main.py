
from fastapi import FastAPI

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


app = FastAPI(
    title="InventoryFlow",
    description="Multi-Tenant Inventory & Order Management Platform",
    version="1.0.0",
)


# Register API routers
app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(product_router)
app.include_router(warehouse_router)
app.include_router(customer_router)
app.include_router(inventory_router)
app.include_router(order_router)
app.include_router(inventory_movement_router)


@app.get("/")
def root():
    return {
        "message": "InventoryFlow API",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }