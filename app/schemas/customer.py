from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    organization_id: int

    name: str = Field(
        min_length=1,
        max_length=150,
    )

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    address: str | None = Field(
        default=None,
        max_length=500,
    )


class CustomerUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    address: str | None = Field(
        default=None,
        max_length=500,
    )


class CustomerResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    email: str | None
    phone: str | None
    address: str | None

    model_config = ConfigDict(
        from_attributes=True
    )