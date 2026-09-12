from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    sku: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    price: Decimal = Field(
        ge=0,
        decimal_places=2,
    )

    is_active: bool = True


class ProductCreate(ProductBase):
    organization_id: int


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


class ProductResponse(ProductBase):
    id: int
    organization_id: int

    model_config = ConfigDict(
        from_attributes=True
    )