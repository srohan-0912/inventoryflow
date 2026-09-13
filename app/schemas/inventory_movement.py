from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.inventory_movement import InventoryMovementType


class InventoryMovementResponse(BaseModel):
    id: int
    organization_id: int
    product_id: int
    warehouse_id: int
    order_id: int | None
    movement_type: InventoryMovementType
    quantity: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)