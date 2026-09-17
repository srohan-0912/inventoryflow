
from app.main import app
from app.api.dependencies import get_current_user
from app.models.user import User, UserRole


def fake_user(role: UserRole):
    return User(
        id=1,
        organization_id=1,
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password",
        role=role,
        is_active=True,
    )


def test_staff_cannot_create_inventory(client):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.STAFF)
    )

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
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.STAFF)
    )

    try:
        response = client.put(
            "/inventory/1",
            json={"quantity": 20},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_adjust_inventory(client):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.STAFF)
    )

    try:
        response = client.patch(
            "/inventory/1/adjust",
            json={"quantity_change": 5},
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_delete_inventory(client):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.STAFF)
    )

    try:
        response = client.delete("/inventory/1")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

        
def test_inventory_rejects_negative_quantity(client):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.OWNER)
    )

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
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.OWNER)
    )

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
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.OWNER)
    )

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