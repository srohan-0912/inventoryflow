
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.permissions import require_roles
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# Create product: OWNER, ADMIN, MANAGER only
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    product = Product(
        organization_id=current_user.organization_id,
        **product_data.model_dump(),
    )

    db.add(product)

    try:
        db.commit()
        db.refresh(product)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Product SKU already exists.",
        )

    return product


# List products: any authenticated user in the organization
@router.get(
    "/",
    response_model=list[ProductResponse],
)
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Product)
        .where(
            Product.organization_id
            == current_user.organization_id
        )
        .order_by(Product.id)
    )

    return db.scalars(statement).all()


# Get one product
@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Product).where(
        Product.id == product_id,
        Product.organization_id
        == current_user.organization_id,
    )

    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    return product


# Update product: any authenticated user for now
@router.put(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Product).where(
        Product.id == product_id,
        Product.organization_id
        == current_user.organization_id,
    )

    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    update_data = product_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Product SKU already exists.",
        )

    return product


# Delete product: any authenticated user for now
@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Product).where(
        Product.id == product_id,
        Product.organization_id
        == current_user.organization_id,
    )

    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    db.delete(product)
    db.commit()

    return None