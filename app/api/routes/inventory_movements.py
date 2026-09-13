from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)
from app.models.user import User
from app.schemas.inventory_movement import InventoryMovementResponse


router = APIRouter(
    prefix="/inventory-movements",
    tags=["Inventory Movements"],
)


# ============================================================
# GET ALL INVENTORY MOVEMENTS
# ============================================================

@router.get(
    "/",
    response_model=list[InventoryMovementResponse],
)
def get_inventory_movements(
    product_id: int | None = Query(default=None),
    warehouse_id: int | None = Query(default=None),
    order_id: int | None = Query(default=None),
    movement_type: InventoryMovementType | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(InventoryMovement).where(
        InventoryMovement.organization_id
        == current_user.organization_id
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


# ============================================================
# GET SINGLE INVENTORY MOVEMENT
# ============================================================

@router.get(
    "/{movement_id}",
    response_model=InventoryMovementResponse,
)
def get_inventory_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(InventoryMovement).where(
        InventoryMovement.id == movement_id,
        InventoryMovement.organization_id
        == current_user.organization_id,
    )

    movement = db.scalar(statement)

    if movement is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory movement not found.",
        )

    return movement