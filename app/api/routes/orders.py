from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.order import OrderCreate, OrderResponse


router = APIRouter(prefix="/orders", tags=["Orders"])


# ============================================================
# CREATE ORDER
# ============================================================

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization_id = current_user.organization_id

    # Check customer
    customer = db.get(Customer, order_data.customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    # Customer must belong to current user's organization
    if customer.organization_id != organization_id:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    # Check warehouse
    warehouse = db.get(Warehouse, order_data.warehouse_id)

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found.",
        )

    # Warehouse must belong to current user's organization
    if warehouse.organization_id != organization_id:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found.",
        )

    # Order must contain at least one item
    if not order_data.items:
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one item.",
        )

    # Create order
    order = Order(
        organization_id=organization_id,
        customer_id=order_data.customer_id,
        warehouse_id=order_data.warehouse_id,
        status=OrderStatus.PENDING,
        total_amount=0,
    )

    db.add(order)

    total_amount = 0

    # Create order items
    for item_data in order_data.items:

        product = db.get(Product, item_data.product_id)

        # Product must exist
        if product is None:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Product {item_data.product_id} not found.",
            )

        # Product must belong to current user's organization
        if product.organization_id != organization_id:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Product {item_data.product_id} not found.",
            )

        # Product must be active
        if not product.is_active:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Product {item_data.product_id} is inactive.",
            )

        # Calculate price
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

    # Set total amount
    order.total_amount = total_amount

    db.commit()
    db.refresh(order)

    return order


# ============================================================
# GET ALL ORDERS
# ============================================================

@router.get(
    "/",
    response_model=list[OrderResponse],
)
def get_orders(
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
    )

    return db.scalars(statement).all()


# ============================================================
# GET SINGLE ORDER
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
# ============================================================

@router.post(
    "/{order_id}/confirm",
    response_model=OrderResponse,
)
def confirm_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lock the order row
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

    # Only pending orders can be confirmed
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Only pending orders can be confirmed.",
        )

    # Check and lock inventory rows
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
                    f"Inventory not found for "
                    f"product {item.product_id}."
                ),
            )

        # Calculate available stock
        available_quantity = (
            inventory.quantity
            - inventory.reserved_quantity
        )

        # Check stock
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

        # Reserve stock
        inventory.reserved_quantity += item.quantity

    # Change order status
    order.status = OrderStatus.CONFIRMED

    db.commit()
    db.refresh(order)

    return order


# ============================================================
# CANCEL ORDER
# ============================================================

@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lock the order row
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

    # Only pending or confirmed orders can be cancelled
    if order.status not in (
        OrderStatus.PENDING,
        OrderStatus.CONFIRMED,
    ):
        raise HTTPException(
            status_code=400,
            detail="This order cannot be cancelled.",
        )

    # If confirmed, release reserved inventory
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
                        f"Inventory not found for "
                        f"product {item.product_id}."
                    ),
                )

            # Safety check
            if inventory.reserved_quantity < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid reserved inventory for "
                        f"product {item.product_id}."
                    ),
                )

            # Release reservation
            inventory.reserved_quantity -= item.quantity

    # Change order status
    order.status = OrderStatus.CANCELLED

    db.commit()
    db.refresh(order)

    return order


# ============================================================
# SHIP ORDER
# ============================================================

@router.post(
    "/{order_id}/ship",
    response_model=OrderResponse,
)
def ship_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lock the order row
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

    # Only confirmed orders can be shipped
    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(
            status_code=400,
            detail="Only confirmed orders can be shipped.",
        )

    # Lock and update inventory
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
                    f"Inventory not found for "
                    f"product {item.product_id}."
                ),
            )

        # Check reserved inventory
        if inventory.reserved_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient reserved inventory for "
                    f"product {item.product_id}."
                ),
            )

        # Check actual inventory
        if inventory.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient inventory for "
                    f"product {item.product_id}."
                ),
            )

        # Deduct sold quantity
        inventory.quantity -= item.quantity

        # Remove reservation
        inventory.reserved_quantity -= item.quantity

        # Record SALE movement
        movement = InventoryMovement(
            organization_id=order.organization_id,
            product_id=item.product_id,
            warehouse_id=order.warehouse_id,
            order_id=order.id,
            movement_type=InventoryMovementType.SALE,
            quantity=-item.quantity,
        )

        db.add(movement)

    # Change order status
    order.status = OrderStatus.SHIPPED

    db.commit()
    db.refresh(order)

    return order


# ============================================================
# COMPLETE ORDER
# ============================================================

@router.post(
    "/{order_id}/complete",
    response_model=OrderResponse,
)
def complete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lock the order row
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

    # Only shipped orders can be completed
    if order.status != OrderStatus.SHIPPED:
        raise HTTPException(
            status_code=400,
            detail="Only shipped orders can be completed.",
        )

    # Change order status
    order.status = OrderStatus.COMPLETED

    db.commit()
    db.refresh(order)

    return order