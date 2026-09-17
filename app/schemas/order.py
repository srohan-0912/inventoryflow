from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    warehouse_id: int
    items: list[OrderItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_products(self):
        product_ids = [
            item.product_id for item in self.items
        ]

        if len(product_ids) != len(set(product_ids)):
            raise ValueError(
                "Each product can appear only once in an order."
            )

        return self


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(
        from_attributes=True
    )


class OrderResponse(BaseModel):
    id: int
    organization_id: int
    customer_id: int
    warehouse_id: int
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]

    model_config = ConfigDict(
        from_attributes=True
    )