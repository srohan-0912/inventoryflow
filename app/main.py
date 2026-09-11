from fastapi import FastAPI

app = FastAPI(
    title="InventoryFlow",
    description="Multi-Tenant Inventory & Order Management Platform",
    version="1.0.0",
)

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

