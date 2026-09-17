from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.permissions import require_roles

from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole
from app.models.warehouse import Warehouse

from app.schemas.order import OrderCreate, OrderResponse


router = APIRouter(prefix="/orders", tags=["Orders"])


# ============================================================
# CREATE ORDER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
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

    customer = db.get(Customer, order_data.customer_id)

    if (
        customer is None
        or customer.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    warehouse = db.get(Warehouse, order_data.warehouse_id)

    if (
        warehouse is None
        or warehouse.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found.",
        )

    if not order_data.items:
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one item.",
        )

    order = Order(
        organization_id=organization_id,
        customer_id=order_data.customer_id,
        warehouse_id=order_data.warehouse_id,
        status=OrderStatus.PENDING,
        total_amount=0,
    )

    db.add(order)

    total_amount = 0

    try:
        for item_data in order_data.items:
            product = db.get(Product, item_data.product_id)

            if (
                product is None
                or product.organization_id != organization_id
            ):
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Product {item_data.product_id} not found."
                    ),
                )

            if not product.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Product {item_data.product_id} is inactive."
                    ),
                )

            unit_price = product.price
            subtotal = unit_price * item_data.quantity

            order_item = OrderItem(
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )

            order.items.append(order_item)
            total_amount += subtotal

        order.total_amount = total_amount

        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    return order


# ============================================================
# GET ALL ORDERS
# ALL AUTHENTICATED USERS
# PAGINATION: skip and limit
# ============================================================

@router.get(
    "/",
    response_model=list[OrderResponse],
)
def get_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Order)
        .where(
            Order.organization_id
            == current_user.organization_id
        )
        .order_by(Order.id)
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


# ============================================================
# GET SINGLE ORDER
# ALL AUTHENTICATED USERS
# ============================================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Order).where(
        Order.id == order_id,
        Order.organization_id
        == current_user.organization_id,
    )

    order = db.scalar(statement)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    return order


# ============================================================
# CONFIRM ORDER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/{order_id}/confirm",
    response_model=OrderResponse,
)
def confirm_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    order = db.scalar(
        select(Order)
        .where(
            Order.id == order_id,
            Order.organization_id
            == current_user.organization_id,
        )
        .with_for_update()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending orders can be confirmed.",
        )

    try:
        for item in order.items:
            inventory = db.scalar(
                select(Inventory)
                .where(
                    Inventory.organization_id
                    == current_user.organization_id,
                    Inventory.product_id == item.product_id,
                    Inventory.warehouse_id == order.warehouse_id,
                )
                .with_for_update()
            )

            if inventory is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Inventory not found for "
                        f"product {item.product_id}."
                    ),
                )

            available_quantity = (
                inventory.quantity
                - inventory.reserved_quantity
            )

            if available_quantity < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient inventory for "
                        f"product {item.product_id}. "
                        f"Available: {available_quantity}, "
                        f"Requested: {item.quantity}."
                    ),
                )

            inventory.reserved_quantity += item.quantity

        order.status = OrderStatus.CONFIRMED

        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    return order


# ============================================================
# CANCEL ORDER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    order = db.scalar(
        select(Order)
        .where(
            Order.id == order_id,
            Order.organization_id
            == current_user.organization_id,
        )
        .with_for_update()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.status not in (
        OrderStatus.PENDING,
        OrderStatus.CONFIRMED,
    ):
        raise HTTPException(
            status_code=400,
            detail="This order cannot be cancelled.",
        )

    try:
        if order.status == OrderStatus.CONFIRMED:
            for item in order.items:
                inventory = db.scalar(
                    select(Inventory)
                    .where(
                        Inventory.organization_id
                        == current_user.organization_id,
                        Inventory.product_id == item.product_id,
                        Inventory.warehouse_id == order.warehouse_id,
                    )
                    .with_for_update()
                )

                if inventory is None:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "Inventory not found for "
                            f"product {item.product_id}."
                        ),
                    )

                if inventory.reserved_quantity < item.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Invalid reserved inventory for "
                            f"product {item.product_id}."
                        ),
                    )

                inventory.reserved_quantity -= item.quantity

        order.status = OrderStatus.CANCELLED

        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    return order


# ============================================================
# SHIP ORDER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/{order_id}/ship",
    response_model=OrderResponse,
)
def ship_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    order = db.scalar(
        select(Order)
        .where(
            Order.id == order_id,
            Order.organization_id
            == current_user.organization_id,
        )
        .with_for_update()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(
            status_code=400,
            detail="Only confirmed orders can be shipped.",
        )

    try:
        for item in order.items:
            inventory = db.scalar(
                select(Inventory)
                .where(
                    Inventory.organization_id
                    == current_user.organization_id,
                    Inventory.product_id == item.product_id,
                    Inventory.warehouse_id == order.warehouse_id,
                )
                .with_for_update()
            )

            if inventory is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Inventory not found for "
                        f"product {item.product_id}."
                    ),
                )

            if inventory.reserved_quantity < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Insufficient reserved inventory for "
                        f"product {item.product_id}."
                    ),
                )

            if inventory.quantity < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Insufficient inventory for "
                        f"product {item.product_id}."
                    ),
                )

            inventory.quantity -= item.quantity
            inventory.reserved_quantity -= item.quantity

            movement = InventoryMovement(
                organization_id=order.organization_id,
                product_id=item.product_id,
                warehouse_id=order.warehouse_id,
                order_id=order.id,
                movement_type=InventoryMovementType.SALE,
                quantity=-item.quantity,
            )

            db.add(movement)

        order.status = OrderStatus.SHIPPED

        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    return order


# ============================================================
# COMPLETE ORDER
# OWNER, ADMIN, MANAGER
# ============================================================

@router.post(
    "/{order_id}/complete",
    response_model=OrderResponse,
)
def complete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.OWNER,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
):
    order = db.scalar(
        select(Order)
        .where(
            Order.id == order_id,
            Order.organization_id
            == current_user.organization_id,
        )
        .with_for_update()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.status != OrderStatus.SHIPPED:
        raise HTTPException(
            status_code=400,
            detail="Only shipped orders can be completed.",
        )

    order.status = OrderStatus.COMPLETED

    db.commit()
    db.refresh(order)

    return order