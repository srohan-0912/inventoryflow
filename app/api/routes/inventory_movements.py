from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)
from app.schemas.inventory_movement import InventoryMovementResponse


router = APIRouter(
    prefix="/inventory-movements",
    tags=["Inventory Movements"],
)


@router.get(
    "/",
    response_model=list[InventoryMovementResponse],
)
def get_inventory_movements(
    organization_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    warehouse_id: int | None = Query(default=None),
    order_id: int | None = Query(default=None),
    movement_type: InventoryMovementType | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    statement = select(InventoryMovement)

    if organization_id is not None:
        statement = statement.where(
            InventoryMovement.organization_id == organization_id
        )

    if product_id is not None:
        statement = statement.where(
            InventoryMovement.product_id == product_id
        )

    if warehouse_id is not None:
        statement = statement.where(
            InventoryMovement.warehouse_id == warehouse_id
        )

    if order_id is not None:
        statement = statement.where(
            InventoryMovement.order_id == order_id
        )

    if movement_type is not None:
        statement = statement.where(
            InventoryMovement.movement_type == movement_type
        )

    statement = (
        statement
        .order_by(InventoryMovement.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


@router.get(
    "/{movement_id}",
    response_model=InventoryMovementResponse,
)
def get_inventory_movement(
    movement_id: int,
    db: Session = Depends(get_db),
):
    movement = db.get(
        InventoryMovement,
        movement_id,
    )

    if movement is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory movement not found.",
        )

    return movement