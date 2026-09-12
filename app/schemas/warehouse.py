from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    organization_id: int
    name: str = Field(
        min_length=1,
        max_length=150,
    )
    location: str | None = Field(
        default=None,
        max_length=255,
    )


class WarehouseUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    location: str | None = Field(
        default=None,
        max_length=255,
    )


class WarehouseResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    location: str | None

    model_config = ConfigDict(
        from_attributes=True
    )