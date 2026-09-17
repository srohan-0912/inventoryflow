from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.permissions import require_roles
from app.models.user import User, UserRole
from app.models.warehouse import Warehouse
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)


router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
)


# ============================================================
# CREATE WAREHOUSE
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    warehouse = Warehouse(
        organization_id=current_user.organization_id,
        **warehouse_data.model_dump(),
    )

    db.add(warehouse)

    try:
        db.commit()
        db.refresh(warehouse)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Warehouse name already exists.",
        )

    return warehouse


# ============================================================
# GET ALL WAREHOUSES
# ALL AUTHENTICATED USERS
# PAGINATION: skip and limit
# ============================================================

@router.get(
    "/",
    response_model=list[WarehouseResponse],
)
def get_warehouses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Warehouse)
        .where(
            Warehouse.organization_id
            == current_user.organization_id
        )
        .order_by(Warehouse.id)
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


# ============================================================
# GET SINGLE WAREHOUSE
# ALL AUTHENTICATED USERS
# ============================================================

@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
)
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.organization_id
        == current_user.organization_id,
    )

    warehouse = db.scalar(statement)

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found.",
        )

    return warehouse


# ============================================================
# UPDATE WAREHOUSE
# OWNER, ADMIN, MANAGER
# ============================================================

@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
)
def update_warehouse(
    warehouse_id: int,
    warehouse_data: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    statement = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.organization_id
        == current_user.organization_id,
    )

    warehouse = db.scalar(statement)

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found.",
        )

    update_data = warehouse_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(warehouse, field, value)

    try:
        db.commit()
        db.refresh(warehouse)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Warehouse name already exists.",
        )

    return warehouse


# ============================================================
# DELETE WAREHOUSE
# OWNER, ADMIN, MANAGER
# ============================================================

@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    statement = select(Warehouse).where(
        Warehouse.id == warehouse_id,
        Warehouse.organization_id
        == current_user.organization_id,
    )

    warehouse = db.scalar(statement)

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found.",
        )

    db.delete(warehouse)
    db.commit()

    return None