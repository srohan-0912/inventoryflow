
from decimal import Decimal

import pytest

from app.main import app
from app.api.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.models.inventory_movement import (
    InventoryMovement,
    InventoryMovementType,
)


# ============================================================
# HELPERS
# ============================================================

def fake_user(role: UserRole, organization_id: int = 1):
    return User(
        id=1,
        organization_id=organization_id,
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password",
        role=role,
        is_active=True,
    )


def authenticate_as(role: UserRole, organization_id: int = 1):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(role, organization_id)
    )


def create_inventory_test_data(db_session):
    organization = Organization(
        name="Test Organization",
    )

    db_session.add(organization)
    db_session.flush()

    product = Product(
        organization_id=organization.id,
        sku="TEST-SKU-001",
        name="Test Product",
        description="Integration test product",
        price=Decimal("100.00"),
        is_active=True,
    )

    warehouse = Warehouse(
        organization_id=organization.id,
        name="Test Warehouse",
        location="Test Location",
    )

    db_session.add_all([product, warehouse])
    db_session.flush()

    return organization, product, warehouse


def create_inventory_record(
    db_session,
    organization,
    product,
    warehouse,
    quantity=20,
    reserved_quantity=5,
):
    inventory = Inventory(
        organization_id=organization.id,
        product_id=product.id,
        warehouse_id=warehouse.id,
        quantity=quantity,
        reserved_quantity=reserved_quantity,
    )

    db_session.add(inventory)
    db_session.flush()

    return inventory


# ============================================================
# STAFF PERMISSION TESTS
# ============================================================

def test_staff_cannot_create_inventory(client):
    authenticate_as(UserRole.STAFF)

    try:
        response = client.post(
            "/inventory/",
            json={
                "product_id": 1,
                "warehouse_id": 1,
                "quantity": 10,
                "reserved_quantity": 0,
            },
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_update_inventory(client):
    authenticate_as(UserRole.STAFF)

    try:
        response = client.put(
            "/inventory/1",
            json={"quantity": 20},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_adjust_inventory(client):
    authenticate_as(UserRole.STAFF)

    try:
        response = client.patch(
            "/inventory/1/adjust",
            json={"quantity_change": 5},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_delete_inventory(client):
    authenticate_as(UserRole.STAFF)

    try:
        response = client.delete("/inventory/1")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ============================================================
# REQUEST VALIDATION TESTS
# ============================================================

def test_inventory_rejects_negative_quantity(client):
    authenticate_as(UserRole.OWNER)

    try:
        response = client.post(
            "/inventory/",
            json={
                "product_id": 1,
                "warehouse_id": 1,
                "quantity": -1,
                "reserved_quantity": 0,
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_inventory_rejects_negative_reserved_quantity(client):
    authenticate_as(UserRole.OWNER)

    try:
        response = client.post(
            "/inventory/",
            json={
                "product_id": 1,
                "warehouse_id": 1,
                "quantity": 10,
                "reserved_quantity": -1,
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_inventory_rejects_reserved_greater_than_quantity(client):
    authenticate_as(UserRole.OWNER)

    try:
        response = client.post(
            "/inventory/",
            json={
                "product_id": 1,
                "warehouse_id": 1,
                "quantity": 5,
                "reserved_quantity": 10,
            },
        )

        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


# ============================================================
# INTEGRATION TESTS
# ============================================================

def test_owner_can_create_inventory(client, db_session):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.post(
            "/inventory/",
            json={
                "product_id": product.id,
                "warehouse_id": warehouse.id,
                "quantity": 50,
                "reserved_quantity": 10,
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["organization_id"] == organization.id
        assert data["product_id"] == product.id
        assert data["warehouse_id"] == warehouse.id
        assert data["quantity"] == 50
        assert data["reserved_quantity"] == 10

        saved_inventory = db_session.get(
            Inventory,
            data["id"],
        )

        assert saved_inventory is not None
        assert saved_inventory.quantity == 50

    finally:
        app.dependency_overrides.clear()


def test_duplicate_inventory_is_rejected(client, db_session):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        payload = {
            "product_id": product.id,
            "warehouse_id": warehouse.id,
            "quantity": 10,
            "reserved_quantity": 0,
        }

        first_response = client.post(
            "/inventory/",
            json=payload,
        )

        assert first_response.status_code == 201

        second_response = client.post(
            "/inventory/",
            json=payload,
        )

        assert second_response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_adjust_inventory_records_movement(
    client,
    db_session,
):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    inventory = create_inventory_record(
        db_session,
        organization,
        product,
        warehouse,
        quantity=20,
        reserved_quantity=5,
    )

    inventory_id = inventory.id

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.patch(
            f"/inventory/{inventory_id}/adjust",
            json={"quantity_change": 10},
        )

        assert response.status_code == 200
        assert response.json()["quantity"] == 30

        movement = (
            db_session.query(InventoryMovement)
            .filter_by(
                organization_id=organization.id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                movement_type=InventoryMovementType.ADJUSTMENT,
            )
            .one()
        )

        assert movement.quantity == 10
        assert movement.order_id is None

    finally:
        app.dependency_overrides.clear()


def test_adjustment_cannot_reduce_below_reserved(
    client,
    db_session,
):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    inventory = create_inventory_record(
        db_session,
        organization,
        product,
        warehouse,
        quantity=20,
        reserved_quantity=10,
    )

    inventory_id = inventory.id

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.patch(
            f"/inventory/{inventory_id}/adjust",
            json={"quantity_change": -15},
        )

        assert response.status_code == 400

        db_session.refresh(inventory)

        assert inventory.quantity == 20
        assert inventory.reserved_quantity == 10

        movement_count = (
            db_session.query(InventoryMovement)
            .filter_by(
                product_id=product.id,
                warehouse_id=warehouse.id,
            )
            .count()
        )

        assert movement_count == 0

    finally:
        app.dependency_overrides.clear()


def test_cannot_access_another_organizations_inventory(
    client,
    db_session,
):
    organization1, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    inventory = create_inventory_record(
        db_session,
        organization1,
        product,
        warehouse,
        quantity=25,
        reserved_quantity=0,
    )

    inventory_id = inventory.id

    organization2 = Organization(
        name="Another Organization",
    )

    db_session.add(organization2)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization2.id)

    try:
        response = client.get(
            f"/inventory/{inventory_id}"
        )

        assert response.status_code == 404

    finally:
        app.dependency_overrides.clear()

        
# ============================================================
# CROSS-TENANT INVENTORY CREATION TESTS
# ============================================================

def test_cannot_create_inventory_with_another_organizations_product(
    client,
    db_session,
):
    organization1, product1, warehouse1 = create_inventory_test_data(
        db_session
    )

    organization2 = Organization(name="Second Organization")
    db_session.add(organization2)
    db_session.flush()

    product2 = Product(
        organization_id=organization2.id,
        sku="FOREIGN-SKU-001",
        name="Foreign Product",
        description="Belongs to another organization",
        price=Decimal("50.00"),
        is_active=True,
    )
    db_session.add(product2)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization1.id)

    try:
        response = client.post(
            "/inventory/",
            json={
                "product_id": product2.id,
                "warehouse_id": warehouse1.id,
                "quantity": 10,
                "reserved_quantity": 0,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Product not found in your organization."
        )

    finally:
        app.dependency_overrides.clear()


def test_cannot_create_inventory_with_another_organizations_warehouse(
    client,
    db_session,
):
    organization1, product1, warehouse1 = create_inventory_test_data(
        db_session
    )

    organization2 = Organization(name="Third Organization")
    db_session.add(organization2)
    db_session.flush()

    warehouse2 = Warehouse(
        organization_id=organization2.id,
        name="Foreign Warehouse",
        location="Another Location",
    )
    db_session.add(warehouse2)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization1.id)

    try:
        response = client.post(
            "/inventory/",
            json={
                "product_id": product1.id,
                "warehouse_id": warehouse2.id,
                "quantity": 10,
                "reserved_quantity": 0,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Warehouse not found in your organization."
        )

    finally:
        app.dependency_overrides.clear()

        
# ============================================================
# INVENTORY ADJUSTMENT EDGE-CASE TESTS
# ============================================================


def test_adjust_inventory_decrease_successfully(client, db_session):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    inventory = create_inventory_record(
        db_session,
        organization,
        product,
        warehouse,
        quantity=20,
        reserved_quantity=5,
    )

    inventory_id = inventory.id
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.patch(
            f"/inventory/{inventory_id}/adjust",
            json={"quantity_change": -10},
        )

        assert response.status_code == 200
        assert response.json()["quantity"] == 10
        assert response.json()["reserved_quantity"] == 5

        movement = (
            db_session.query(InventoryMovement)
            .filter_by(
                organization_id=organization.id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                movement_type=InventoryMovementType.ADJUSTMENT,
            )
            .one()
        )

        assert movement.quantity == -10
        assert movement.order_id is None

    finally:
        app.dependency_overrides.clear()


def test_adjust_inventory_cannot_make_quantity_negative(
    client,
    db_session,
):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    inventory = create_inventory_record(
        db_session,
        organization,
        product,
        warehouse,
        quantity=10,
        reserved_quantity=0,
    )

    inventory_id = inventory.id
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.patch(
            f"/inventory/{inventory_id}/adjust",
            json={"quantity_change": -11},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Inventory quantity cannot be negative."
        )

        db_session.refresh(inventory)

        assert inventory.quantity == 10
        assert inventory.reserved_quantity == 0

        movement_count = (
            db_session.query(InventoryMovement)
            .filter_by(
                organization_id=organization.id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                movement_type=InventoryMovementType.ADJUSTMENT,
            )
            .count()
        )

        assert movement_count == 0

    finally:
        app.dependency_overrides.clear()


def test_adjust_inventory_can_reduce_to_reserved_quantity(
    client,
    db_session,
):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    inventory = create_inventory_record(
        db_session,
        organization,
        product,
        warehouse,
        quantity=20,
        reserved_quantity=10,
    )

    inventory_id = inventory.id
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.patch(
            f"/inventory/{inventory_id}/adjust",
            json={"quantity_change": -10},
        )

        assert response.status_code == 200
        assert response.json()["quantity"] == 10
        assert response.json()["reserved_quantity"] == 10

        movement = (
            db_session.query(InventoryMovement)
            .filter_by(
                organization_id=organization.id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                movement_type=InventoryMovementType.ADJUSTMENT,
            )
            .one()
        )

        assert movement.quantity == -10

    finally:
        app.dependency_overrides.clear()


def test_zero_inventory_adjustment_records_zero_movement(
    client,
    db_session,
):
    organization, product, warehouse = (
        create_inventory_test_data(db_session)
    )

    inventory = create_inventory_record(
        db_session,
        organization,
        product,
        warehouse,
        quantity=20,
        reserved_quantity=5,
    )

    inventory_id = inventory.id
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.patch(
            f"/inventory/{inventory_id}/adjust",
            json={"quantity_change": 0},
        )

        assert response.status_code == 200
        assert response.json()["quantity"] == 20
        assert response.json()["reserved_quantity"] == 5

        movement = (
            db_session.query(InventoryMovement)
            .filter_by(
                organization_id=organization.id,
                product_id=product.id,
                warehouse_id=warehouse.id,
                movement_type=InventoryMovementType.ADJUSTMENT,
            )
            .one()
        )

        assert movement.quantity == 0

    finally:
        app.dependency_overrides.clear()

        
# ============================================================
# ADDITIONAL TENANT ISOLATION TESTS
# ============================================================

def test_list_inventory_returns_only_own_organization(
    client,
    db_session,
):
    org1, product1, warehouse1 = create_inventory_test_data(
        db_session
    )

    org2 = Organization(name="Second Inventory Organization")
    db_session.add(org2)
    db_session.flush()

    product2 = Product(
        organization_id=org2.id,
        sku="ORG2-SKU-001",
        name="Organization Two Product",
        description="Private product",
        price=Decimal("200.00"),
        is_active=True,
    )

    warehouse2 = Warehouse(
        organization_id=org2.id,
        name="Organization Two Warehouse",
        location="Private Location",
    )

    db_session.add_all([product2, warehouse2])
    db_session.flush()

    inventory1 = create_inventory_record(
        db_session, org1, product1, warehouse1,
        quantity=20, reserved_quantity=5,
    )

    inventory2 = create_inventory_record(
        db_session, org2, product2, warehouse2,
        quantity=99, reserved_quantity=0,
    )

    authenticate_as(UserRole.STAFF, org1.id)

    try:
        response = client.get("/inventory/")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == inventory1.id
        assert data[0]["organization_id"] == org1.id
        assert data[0]["id"] != inventory2.id
    finally:
        app.dependency_overrides.clear()


def test_cannot_update_another_organizations_inventory(
    client,
    db_session,
):
    org1, product, warehouse = create_inventory_test_data(
        db_session
    )

    inventory = create_inventory_record(
        db_session,
        org1,
        product,
        warehouse,
        quantity=25,
        reserved_quantity=5,
    )

    inventory_id = inventory.id

    org2 = Organization(name="Unauthorized Update Organization")
    db_session.add(org2)
    db_session.flush()

    authenticate_as(UserRole.OWNER, org2.id)

    try:
        response = client.put(
            f"/inventory/{inventory_id}",
            json={"quantity": 999},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Inventory not found."

        db_session.refresh(inventory)
        assert inventory.quantity == 25
        assert inventory.reserved_quantity == 5
    finally:
        app.dependency_overrides.clear()


def test_cannot_adjust_another_organizations_inventory(
    client,
    db_session,
):
    org1, product, warehouse = create_inventory_test_data(
        db_session
    )

    inventory = create_inventory_record(
        db_session,
        org1,
        product,
        warehouse,
        quantity=25,
        reserved_quantity=5,
    )

    inventory_id = inventory.id

    org2 = Organization(name="Unauthorized Adjustment Organization")
    db_session.add(org2)
    db_session.flush()

    authenticate_as(UserRole.OWNER, org2.id)

    try:
        response = client.patch(
            f"/inventory/{inventory_id}/adjust",
            json={"quantity_change": 10},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Inventory not found."

        db_session.refresh(inventory)
        assert inventory.quantity == 25

        movement_count = (
            db_session.query(InventoryMovement)
            .filter_by(
                organization_id=org1.id,
                product_id=product.id,
                warehouse_id=warehouse.id,
            )
            .count()
        )

        assert movement_count == 0
    finally:
        app.dependency_overrides.clear()


def test_cannot_delete_another_organizations_inventory(
    client,
    db_session,
):
    org1, product, warehouse = create_inventory_test_data(
        db_session
    )

    inventory = create_inventory_record(
        db_session,
        org1,
        product,
        warehouse,
        quantity=25,
        reserved_quantity=5,
    )

    inventory_id = inventory.id

    org2 = Organization(name="Unauthorized Delete Organization")
    db_session.add(org2)
    db_session.flush()

    authenticate_as(UserRole.OWNER, org2.id)

    try:
        response = client.delete(
            f"/inventory/{inventory_id}"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Inventory not found."

        assert db_session.get(Inventory, inventory_id) is not None
    finally:
        app.dependency_overrides.clear()