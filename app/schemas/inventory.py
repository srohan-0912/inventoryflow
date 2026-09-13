from pydantic import BaseModel, ConfigDict, Field


class InventoryCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int = Field(default=0, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    reserved_quantity: int | None = Field(default=None, ge=0)


class InventoryAdjust(BaseModel):
    quantity_change: int


class InventoryResponse(BaseModel):
    id: int
    organization_id: int
    product_id: int
    warehouse_id: int
    quantity: int
    reserved_quantity: int

    model_config = ConfigDict(
        from_attributes=True
    )