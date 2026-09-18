
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.permissions import require_roles
from app.core.cache import (
    get_cached_json,
    set_cached_json,
    invalidate_product_cache,
    product_list_cache_key,
    product_detail_cache_key,
)
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


# ============================================================
# CREATE PRODUCT
# OWNER, ADMIN, MANAGER
# ============================================================

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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product SKU already exists.",
        )

    # Clear cached product data for this organization.
    invalidate_product_cache(current_user.organization_id)

    return product


# ============================================================
# GET ALL PRODUCTS
# ALL AUTHENTICATED USERS
# PAGINATION + REDIS CACHE
# ============================================================

@router.get(
    "/",
    response_model=list[ProductResponse],
)
def get_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization_id = current_user.organization_id

    cache_key = product_list_cache_key(
        organization_id,
        skip,
        limit,
    )

    cached_products = get_cached_json(cache_key)

    if cached_products is not None:
        return cached_products

    statement = (
        select(Product)
        .where(
            Product.organization_id == organization_id
        )
        .order_by(Product.id)
        .offset(skip)
        .limit(limit)
    )

    products = db.scalars(statement).all()

    # Cache JSON-compatible response data.
    response_data = [
        ProductResponse.model_validate(product).model_dump(mode="json")
        for product in products
    ]

    set_cached_json(cache_key, response_data)

    return response_data


# ============================================================
# GET SINGLE PRODUCT
# ALL AUTHENTICATED USERS
# REDIS CACHE
# ============================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization_id = current_user.organization_id

    cache_key = product_detail_cache_key(
        organization_id,
        product_id,
    )

    cached_product = get_cached_json(cache_key)

    if cached_product is not None:
        return cached_product

    statement = select(Product).where(
        Product.id == product_id,
        Product.organization_id == organization_id,
    )

    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    response_data = ProductResponse.model_validate(
        product
    ).model_dump(mode="json")

    set_cached_json(cache_key, response_data)

    return response_data


# ============================================================
# UPDATE PRODUCT
# OWNER, ADMIN, MANAGER
# INVALIDATE CACHE AFTER SUCCESS
# ============================================================

@router.put(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    organization_id = current_user.organization_id

    statement = select(Product).where(
        Product.id == product_id,
        Product.organization_id == organization_id,
    )

    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product SKU already exists.",
        )

    invalidate_product_cache(organization_id)

    return product


# ============================================================
# DELETE PRODUCT
# OWNER, ADMIN, MANAGER
# INVALIDATE CACHE AFTER SUCCESS
# ============================================================

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    organization_id = current_user.organization_id

    statement = select(Product).where(
        Product.id == product_id,
        Product.organization_id == organization_id,
    )

    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    db.delete(product)
    db.commit()

    invalidate_product_cache(organization_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)