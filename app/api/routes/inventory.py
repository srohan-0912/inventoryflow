
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.permissions import require_roles
from app.models.inventory import Inventory
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.user import User, UserRole
from app.schemas.inventory import (
    InventoryAdjust,
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
)


router = APIRouter(prefix="/inventory", tags=["Inventory"])


WRITE_ROLES = (
    UserRole.OWNER,
    UserRole.ADMIN,
    UserRole.MANAGER,
)


def validate_product_and_warehouse(
    db: Session,
    organization_id: int,
    product_id: int,
    warehouse_id: int,
):
    """Ensure product and warehouse belong to the user's organization."""

    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.organization_id == organization_id,
        )
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found in your organization.",
        )

    warehouse = db.scalar(
        select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.organization_id == organization_id,
        )
    )

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found in your organization.",
        )


# ============================================================
# CREATE INVENTORY
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
):
    if inventory_data.reserved_quantity > inventory_data.quantity:
        raise HTTPException(
            status_code=400,
            detail="Reserved quantity cannot exceed quantity.",
        )

    validate_product_and_warehouse(
        db=db,
        organization_id=current_user.organization_id,
        product_id=inventory_data.product_id,
        warehouse_id=inventory_data.warehouse_id,
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
# ALL AUTHENTICATED USERS
# ============================================================

@router.get("/", response_model=list[InventoryResponse])
def get_inventory(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Inventory)
        .where(
            Inventory.organization_id == current_user.organization_id
        )
        .order_by(Inventory.id)
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


# ============================================================
# GET SINGLE INVENTORY ITEM
# ALL AUTHENTICATED USERS
# ============================================================

@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory_item(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.organization_id == current_user.organization_id,
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
# OWNER, ADMIN, MANAGER
# ============================================================

@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(
    inventory_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
):
    statement = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.organization_id == current_user.organization_id,
    )

    inventory = db.scalar(statement)

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found.",
        )

    update_data = inventory_data.model_dump(exclude_unset=True)

    # Reject explicit null values for quantity fields.
    if any(
        update_data.get(field) is None
        for field in ("quantity", "reserved_quantity")
        if field in update_data
    ):
        raise HTTPException(
            status_code=422,
            detail="Quantity fields cannot be null.",
        )

    new_quantity = update_data.get("quantity", inventory.quantity)
    new_reserved = update_data.get(
        "reserved_quantity",
        inventory.reserved_quantity,
    )

    if new_quantity < 0 or new_reserved < 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity fields cannot be negative.",
        )

    if new_reserved > new_quantity:
        raise HTTPException(
            status_code=400,
            detail="Reserved quantity cannot exceed quantity.",
        )

    for field, value in update_data.items():
        setattr(inventory, field, value)

    try:
        db.commit()
        db.refresh(inventory)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Inventory update failed due to a data conflict.",
        )

    return inventory


# ============================================================
# ADJUST INVENTORY
# OWNER, ADMIN, MANAGER
# ============================================================


@router.patch(
    "/{inventory_id}/adjust",
    response_model=InventoryResponse,
)
def adjust_inventory(
    inventory_id: int,
    adjustment: InventoryAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
):
    statement = (
        select(Inventory)
        .where(
            Inventory.id == inventory_id,
            Inventory.organization_id == current_user.organization_id,
        )
        .with_for_update()
    )

    inventory = db.scalar(statement)

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found.",
        )

    new_quantity = inventory.quantity + adjustment.quantity_change

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

    try:
        inventory.quantity = new_quantity

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

    except Exception:
        db.rollback()
        raise

    return inventory


# ============================================================
# DELETE INVENTORY
# OWNER, ADMIN, MANAGER
# ============================================================

@router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_inventory(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
):
    statement = select(Inventory).where(
        Inventory.id == inventory_id,
        Inventory.organization_id == current_user.organization_id,
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