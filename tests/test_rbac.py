
import pytest

from app.main import app
from app.api.dependencies import get_current_user
from app.api.permissions import require_roles
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


def test_staff_cannot_create_product(client):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.STAFF)
    )

    try:
        response = client.post(
            "/products/",
            json={
                "name": "Test Product",
                "sku": "TEST-001",
                "description": "Test",
                "price": 100,
            },
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_update_product(client):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.STAFF)
    )

    try:
        response = client.put(
            "/products/1",
            json={
                "name": "Updated Product",
                "sku": "TEST-001",
                "description": "Updated",
                "price": 150,
            },
        )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_delete_product(client):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(UserRole.STAFF)
    )

    try:
        response = client.delete("/products/1")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "role",
    [
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
    ],
)
def test_authorized_roles_pass_product_write_permission(role):
    permission_check = require_roles(
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
    )

    user = fake_user(role)

    assert permission_check(user) == user