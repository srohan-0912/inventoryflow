from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(ge=0, decimal_places=2)
    is_active: bool = True


class ProductUpdate(BaseModel):
    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    price: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    organization_id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)