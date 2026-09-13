from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.inventory import Inventory
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)
from app.models.user import User
from app.schemas.inventory import (
    InventoryAdjust,
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
)


router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ============================================================
# CREATE INVENTORY
# ============================================================

@router.post(
    "/",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if inventory_data.reserved_quantity > inventory_data.quantity:
        raise HTTPException(
            status_code=400,
            detail="Reserved quantity cannot exceed quantity.",
        )

    inventory = Inventory(
        organization_id=current_user.organization_id,
        **inventory_data.model_dump(),
    )

    db.add(inventory)

    try:
        db.commit()
        db.refresh(inventory)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Inventory already exists for this product and warehouse.",
        )

    return inventory


# ============================================================
# GET ALL INVENTORY
# ============================================================

@router.get(
    "/",
    response_model=list[InventoryResponse],
)
def get_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Inventory)
        .where(
            Inventory.organization_id
            == current_user.organization_id
        )
        .order_by(Inventory.id)
    )

    return db.scalars(statement).all()


# ============================================================
# GET SINGLE INVENTORY
# ============================================================

@router.get(
    "/{inventory_id}",
    response_model=InventoryResponse,
)
def get_inventory_item(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.organization_id
        == current_user.organization_id,
    )

    inventory = db.scalar(statement)

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found.",
        )

    return inventory


# ============================================================
# UPDATE INVENTORY
# ============================================================

@router.put(
    "/{inventory_id}",
    response_model=InventoryResponse,
)
def update_inventory(
    inventory_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.organization_id
        == current_user.organization_id,
    )

    inventory = db.scalar(statement)

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found.",
        )

    update_data = inventory_data.model_dump(
        exclude_unset=True
    )

    new_quantity = update_data.get(
        "quantity",
        inventory.quantity,
    )

    new_reserved = update_data.get(
        "reserved_quantity",
        inventory.reserved_quantity,
    )

    if new_reserved > new_quantity:
        raise HTTPException(
            status_code=400,
            detail="Reserved quantity cannot exceed quantity.",
        )

    for field, value in update_data.items():
        setattr(inventory, field, value)

    db.commit()
    db.refresh(inventory)

    return inventory


# ============================================================
# ADJUST INVENTORY
# ============================================================

@router.patch(
    "/{inventory_id}/adjust",
    response_model=InventoryResponse,
)
def adjust_inventory(
    inventory_id: int,
    adjustment: InventoryAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Inventory)
        .where(
            Inventory.id == inventory_id,
            Inventory.organization_id
            == current_user.organization_id,
        )
        .with_for_update()
    )

    inventory = db.scalar(statement)

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found.",
        )

    new_quantity = (
        inventory.quantity
        + adjustment.quantity_change
    )

    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Inventory quantity cannot be negative.",
        )

    if inventory.reserved_quantity > new_quantity:
        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be lower than reserved quantity.",
        )

    # Update inventory
    inventory.quantity = new_quantity

    # Create audit record
    movement = InventoryMovement(
        organization_id=inventory.organization_id,
        product_id=inventory.product_id,
        warehouse_id=inventory.warehouse_id,
        movement_type=InventoryMovementType.ADJUSTMENT,
        quantity=adjustment.quantity_change,
    )

    db.add(movement)

    db.commit()
    db.refresh(inventory)

    return inventory


# ============================================================
# DELETE INVENTORY
# ============================================================

@router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_inventory(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.organization_id
        == current_user.organization_id,
    )

    inventory = db.scalar(statement)

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found.",
        )

    db.delete(inventory)

    db.commit()

    return None