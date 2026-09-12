from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    organization_id: int
    customer_id: int
    warehouse_id: int
    items: list[OrderItemCreate]


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    organization_id: int
    customer_id: int
    warehouse_id: int
    status: str
    total_amount: Decimal
    items: list[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)