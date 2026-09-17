
from decimal import Decimal

import pytest

from app.main import app
from app.api.dependencies import get_current_user
from app.models.organization import Organization
from app.models.customer import Customer
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from sqlalchemy import select


# ============================================================
# HELPERS
# ============================================================

def fake_user(role: UserRole, organization_id: int):
    return User(
        id=1,
        organization_id=organization_id,
        name="Order Test User",
        email="order-test@example.com",
        password_hash="not-a-real-password",
        role=role,
        is_active=True,
    )


def authenticate_as(role: UserRole, organization_id: int):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(role, organization_id)
    )


def create_order_test_data(db_session, quantity=20):
    organization = Organization(name="Order Test Organization")
    db_session.add(organization)
    db_session.flush()

    customer = Customer(
        organization_id=organization.id,
        name="Test Customer",
        email="customer@example.com",
        phone="1234567890",
        address="Test Address",
    )

    warehouse = Warehouse(
        organization_id=organization.id,
        name="Order Test Warehouse",
        location="Test Location",
    )

    product = Product(
        organization_id=organization.id,
        sku="ORDER-SKU-001",
        name="Order Test Product",
        description="Product for order tests",
        price=Decimal("100.00"),
        is_active=True,
    )

    db_session.add_all([customer, warehouse, product])
    db_session.flush()

    inventory = Inventory(
        organization_id=organization.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=quantity,
        reserved_quantity=0,
    )

    db_session.add(inventory)
    db_session.flush()

    return organization, customer, warehouse, product, inventory


def create_order(client, customer, warehouse, product, quantity=2):
    return client.post(
        "/orders/",
        json={
            "customer_id": customer.id,
            "warehouse_id": warehouse.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": quantity,
                }
            ],
        },
    )


# ============================================================
# ORDER CREATION
# ============================================================

def test_owner_can_create_order_and_calculate_total(
    client,
    db_session,
):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client,
            customer,
            warehouse,
            product,
            quantity=3,
        )

        assert response.status_code == 201

        data = response.json()

        assert data["organization_id"] == organization.id
        assert data["customer_id"] == customer.id
        assert data["warehouse_id"] == warehouse.id
        assert data["status"] == "PENDING"
        assert Decimal(data["total_amount"]) == Decimal("300.00")

        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == product.id
        assert data["items"][0]["quantity"] == 3
        assert Decimal(data["items"][0]["unit_price"]) == Decimal("100.00")
        assert Decimal(data["items"][0]["subtotal"]) == Decimal("300.00")

    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_create_order(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.STAFF, organization.id)

    try:
        response = create_order(
            client,
            customer,
            warehouse,
            product,
        )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()


def test_order_rejects_zero_quantity(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.post(
            "/orders/",
            json={
                "customer_id": customer.id,
                "warehouse_id": warehouse.id,
                "items": [
                    {
                        "product_id": product.id,
                        "quantity": 0,
                    }
                ],
            },
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


# ============================================================
# TENANT ISOLATION
# ============================================================

def test_cannot_create_order_for_another_organizations_customer(
    client,
    db_session,
):
    organization1, customer1, warehouse1, product1, inventory1 = (
        create_order_test_data(db_session)
    )

    organization2 = Organization(name="Foreign Customer Organization")
    db_session.add(organization2)
    db_session.flush()

    foreign_customer = Customer(
        organization_id=organization2.id,
        name="Foreign Customer",
    )
    db_session.add(foreign_customer)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization1.id)

    try:
        response = client.post(
            "/orders/",
            json={
                "customer_id": foreign_customer.id,
                "warehouse_id": warehouse1.id,
                "items": [
                    {
                        "product_id": product1.id,
                        "quantity": 1,
                    }
                ],
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Customer not found."

    finally:
        app.dependency_overrides.clear()


def test_cannot_create_order_with_another_organizations_product(
    client,
    db_session,
):
    organization1, customer1, warehouse1, product1, inventory1 = (
        create_order_test_data(db_session)
    )

    organization2 = Organization(name="Foreign Product Organization")
    db_session.add(organization2)
    db_session.flush()

    foreign_product = Product(
        organization_id=organization2.id,
        sku="FOREIGN-ORDER-SKU",
        name="Foreign Product",
        description="Belongs to another organization",
        price=Decimal("50.00"),
        is_active=True,
    )
    db_session.add(foreign_product)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization1.id)

    try:
        response = client.post(
            "/orders/",
            json={
                "customer_id": customer1.id,
                "warehouse_id": warehouse1.id,
                "items": [
                    {
                        "product_id": foreign_product.id,
                        "quantity": 1,
                    }
                ],
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            f"Product {foreign_product.id} not found."
        )

    finally:
        app.dependency_overrides.clear()


def test_cannot_read_another_organizations_order(
    client,
    db_session,
):
    organization1, customer1, warehouse1, product1, inventory1 = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization1.id)

    try:
        create_response = create_order(
            client,
            customer1,
            warehouse1,
            product1,
        )

        assert create_response.status_code == 201
        order_id = create_response.json()["id"]

    finally:
        app.dependency_overrides.clear()

    organization2 = Organization(name="Other Order Organization")
    db_session.add(organization2)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization2.id)

    try:
        response = client.get(f"/orders/{order_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Order not found."

    finally:
        app.dependency_overrides.clear()


# ============================================================
# ORDER WORKFLOW
# ============================================================

def test_confirm_order_reserves_inventory(
    client,
    db_session,
):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session, quantity=20)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        create_response = create_order(
            client,
            customer,
            warehouse,
            product,
            quantity=5,
        )
        assert create_response.status_code == 201

        order_id = create_response.json()["id"]

        confirm_response = client.post(
            f"/orders/{order_id}/confirm"
        )

        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "CONFIRMED"

        db_session.refresh(inventory)
        assert inventory.quantity == 20
        assert inventory.reserved_quantity == 5

    finally:
        app.dependency_overrides.clear()


def test_confirm_order_rejects_insufficient_inventory(
    client,
    db_session,
):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session, quantity=3)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        create_response = create_order(
            client,
            customer,
            warehouse,
            product,
            quantity=5,
        )
        assert create_response.status_code == 201, create_response.text

        order_id = create_response.json()["id"]

        confirm_response = client.post(
            f"/orders/{order_id}/confirm"
        )

        assert confirm_response.status_code == 400
        assert "Insufficient inventory" in (
            confirm_response.json()["detail"]
        )

        db_session.refresh(inventory)
        assert inventory.quantity == 3
        assert inventory.reserved_quantity == 0

    finally:
        app.dependency_overrides.clear()


# ============================================================
# REMAINING ORDER LIFECYCLE TESTS
# ============================================================

def test_cancel_pending_order(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client, customer, warehouse, product, quantity=2
        )
        assert response.status_code == 201
        order_id = response.json()["id"]

        cancel_response = client.post(
            f"/orders/{order_id}/cancel"
        )

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "CANCELLED"

        db_session.refresh(inventory)
        assert inventory.quantity == 20
        assert inventory.reserved_quantity == 0

    finally:
        app.dependency_overrides.clear()


def test_cancel_confirmed_order_releases_reserved_inventory(
    client, db_session
):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client, customer, warehouse, product, quantity=4
        )
        assert response.status_code == 201
        order_id = response.json()["id"]

        confirm_response = client.post(
            f"/orders/{order_id}/confirm"
        )
        assert confirm_response.status_code == 200

        db_session.refresh(inventory)
        assert inventory.reserved_quantity == 4

        cancel_response = client.post(
            f"/orders/{order_id}/cancel"
        )

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "CANCELLED"

        db_session.refresh(inventory)
        assert inventory.quantity == 20
        assert inventory.reserved_quantity == 0

    finally:
        app.dependency_overrides.clear()


def test_ship_confirmed_order_updates_inventory_and_movement(
    client, db_session
):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client, customer, warehouse, product, quantity=3
        )
        assert response.status_code == 201
        order_id = response.json()["id"]

        confirm_response = client.post(
            f"/orders/{order_id}/confirm"
        )
        assert confirm_response.status_code == 200

        ship_response = client.post(
            f"/orders/{order_id}/ship"
        )

        assert ship_response.status_code == 200
        assert ship_response.json()["status"] == "SHIPPED"

        db_session.refresh(inventory)
        assert inventory.quantity == 17
        assert inventory.reserved_quantity == 0

        movement = db_session.scalar(
            select(InventoryMovement).where(
                InventoryMovement.order_id == order_id
            )
        )

        assert movement is not None
        assert movement.organization_id == organization.id
        assert movement.product_id == product.id
        assert movement.warehouse_id == warehouse.id
        assert movement.movement_type == InventoryMovementType.SALE
        assert movement.quantity == -3

    finally:
        app.dependency_overrides.clear()


def test_complete_shipped_order(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client, customer, warehouse, product, quantity=2
        )
        assert response.status_code == 201
        order_id = response.json()["id"]

        confirm_response = client.post(
            f"/orders/{order_id}/confirm"
        )
        assert confirm_response.status_code == 200

        ship_response = client.post(
            f"/orders/{order_id}/ship"
        )
        assert ship_response.status_code == 200

        complete_response = client.post(
            f"/orders/{order_id}/complete"
        )

        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "COMPLETED"

    finally:
        app.dependency_overrides.clear()


def test_cannot_ship_pending_order(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client, customer, warehouse, product, quantity=2
        )
        assert response.status_code == 201
        order_id = response.json()["id"]

        ship_response = client.post(
            f"/orders/{order_id}/ship"
        )

        assert ship_response.status_code == 400
        assert ship_response.json()["detail"] == (
            "Only confirmed orders can be shipped."
        )

        db_session.refresh(inventory)
        assert inventory.quantity == 20
        assert inventory.reserved_quantity == 0

    finally:
        app.dependency_overrides.clear()


def test_cannot_complete_pending_order(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client, customer, warehouse, product, quantity=2
        )
        assert response.status_code == 201
        order_id = response.json()["id"]

        complete_response = client.post(
            f"/orders/{order_id}/complete"
        )

        assert complete_response.status_code == 400
        assert complete_response.json()["detail"] == (
            "Only shipped orders can be completed."
        )

    finally:
        app.dependency_overrides.clear()


def test_cannot_cancel_shipped_order(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_order(
            client, customer, warehouse, product, quantity=2
        )
        assert response.status_code == 201
        order_id = response.json()["id"]

        assert client.post(
            f"/orders/{order_id}/confirm"
        ).status_code == 200

        assert client.post(
            f"/orders/{order_id}/ship"
        ).status_code == 200

        cancel_response = client.post(
            f"/orders/{order_id}/cancel"
        )

        assert cancel_response.status_code == 400
        assert cancel_response.json()["detail"] == (
            "This order cannot be cancelled."
        )

    finally:
        app.dependency_overrides.clear()


# ============================================================
# MULTI-ITEM ORDER TESTS
# ============================================================

def test_create_multi_item_order_calculates_total(client, db_session):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session)
    )

    # Use the generated organization ID, not a hardcoded ID.
    authenticate_as(UserRole.OWNER, organization_id=organization.id)

    try:
        second_product = Product(
            organization_id=organization.id,
            sku="ORDER-SKU-002",
            name="Second Order Product",
            description="Second product for multi-item tests",
            price=Decimal("25.00"),
            is_active=True,
        )
        db_session.add(second_product)
        db_session.flush()

        response = client.post(
            "/orders/",
            json={
                "customer_id": customer.id,
                "warehouse_id": warehouse.id,
                "items": [
                    {"product_id": product.id, "quantity": 2},
                    {"product_id": second_product.id, "quantity": 3},
                ],
            },
        )

        assert response.status_code == 201, response.json()

        data = response.json()

        assert Decimal(str(data["total_amount"])) == Decimal("275.00")
        assert len(data["items"]) == 2

        items_by_product = {
            item["product_id"]: item for item in data["items"]
        }

        assert Decimal(
            str(items_by_product[product.id]["subtotal"])
        ) == Decimal("200.00")

        assert Decimal(
            str(items_by_product[second_product.id]["subtotal"])
        ) == Decimal("75.00")

    finally:
        app.dependency_overrides.clear()


def test_multi_item_confirmation_failure_rolls_back_all_reservations(
    client, db_session
):
    organization, customer, warehouse, product, inventory = (
        create_order_test_data(db_session, quantity=20)
    )

    # Use the generated organization ID, not a hardcoded ID.
    authenticate_as(UserRole.OWNER, organization_id=organization.id)

    try:
        second_product = Product(
            organization_id=organization.id,
            sku="ORDER-SKU-003",
            name="Limited Stock Product",
            description="Product with limited stock",
            price=Decimal("25.00"),
            is_active=True,
        )
        db_session.add(second_product)
        db_session.flush()

        second_inventory = Inventory(
            organization_id=organization.id,
            product_id=second_product.id,
            warehouse_id=warehouse.id,
            quantity=2,
            reserved_quantity=0,
        )
        db_session.add(second_inventory)
        db_session.flush()

        order_response = client.post(
            "/orders/",
            json={
                "customer_id": customer.id,
                "warehouse_id": warehouse.id,
                "items": [
                    {"product_id": product.id, "quantity": 4},
                    {"product_id": second_product.id, "quantity": 3},
                ],
            },
        )

        assert order_response.status_code == 201, order_response.json()

        order_id = order_response.json()["id"]

        confirm_response = client.post(
            f"/orders/{order_id}/confirm"
        )

        assert confirm_response.status_code == 400
        assert "Insufficient inventory" in (
            confirm_response.json()["detail"]
        )

        db_session.refresh(inventory)
        db_session.refresh(second_inventory)

        # Failed confirmation must not leave partial reservations.
        assert inventory.quantity == 20
        assert inventory.reserved_quantity == 0

        assert second_inventory.quantity == 2
        assert second_inventory.reserved_quantity == 0

        order = db_session.get(Order, order_id)
        db_session.refresh(order)

        assert order.status == OrderStatus.PENDING

    finally:
        app.dependency_overrides.clear()