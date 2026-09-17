from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.permissions import require_roles
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)


router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


# ============================================================
# CREATE CUSTOMER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    customer = Customer(
        organization_id=current_user.organization_id,
        **customer_data.model_dump(),
    )

    db.add(customer)

    try:
        db.commit()
        db.refresh(customer)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Customer could not be created due to a data conflict.",
        )

    return customer


# ============================================================
# GET ALL CUSTOMERS
# ALL AUTHENTICATED USERS
# PAGINATION: skip and limit
# ============================================================

@router.get(
    "/",
    response_model=list[CustomerResponse],
)
def get_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Customer)
        .where(
            Customer.organization_id
            == current_user.organization_id
        )
        .order_by(Customer.id)
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


# ============================================================
# GET SINGLE CUSTOMER
# ALL AUTHENTICATED USERS
# ============================================================

@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Customer).where(
        Customer.id == customer_id,
        Customer.organization_id
        == current_user.organization_id,
    )

    customer = db.scalar(statement)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    return customer


# ============================================================
# UPDATE CUSTOMER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    statement = select(Customer).where(
        Customer.id == customer_id,
        Customer.organization_id
        == current_user.organization_id,
    )

    customer = db.scalar(statement)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    update_data = customer_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(customer, field, value)

    try:
        db.commit()
        db.refresh(customer)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Customer could not be updated due to a data conflict.",
        )

    return customer


# ============================================================
# DELETE CUSTOMER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    statement = select(Customer).where(
        Customer.id == customer_id,
        Customer.organization_id
        == current_user.organization_id,
    )

    customer = db.scalar(statement)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    db.delete(customer)
    db.commit()

    return None