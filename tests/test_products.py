
from decimal import Decimal

from app.main import app
from app.api.dependencies import get_current_user
from app.models.organization import Organization
from app.models.product import Product
from app.models.user import User, UserRole


# ============================================================
# HELPERS
# ============================================================

def fake_user(role: UserRole, organization_id: int):
    return User(
        id=1,
        organization_id=organization_id,
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-password",
        role=role,
        is_active=True,
    )


def authenticate_as(role: UserRole, organization_id: int):
    app.dependency_overrides[get_current_user] = (
        lambda: fake_user(role, organization_id)
    )


def create_organization(db_session, name="Product Test Org"):
    organization = Organization(name=name)
    db_session.add(organization)
    db_session.flush()
    return organization


def product_payload(sku="SKU-001", name="Test Product"):
    return {
        "sku": sku,
        "name": name,
        "description": "Integration test product",
        "price": "100.00",
        "is_active": True,
    }


# ============================================================
# CREATE TESTS
# ============================================================

def test_owner_can_create_product(client, db_session):
    organization = create_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.post(
            "/products/",
            json=product_payload(),
        )

        assert response.status_code == 201

        data = response.json()
        assert data["organization_id"] == organization.id
        assert data["sku"] == "SKU-001"
        assert data["name"] == "Test Product"
        assert Decimal(str(data["price"])) == Decimal("100.00")

        saved = db_session.get(Product, data["id"])
        assert saved is not None
        assert saved.organization_id == organization.id

    finally:
        app.dependency_overrides.clear()


def test_duplicate_product_sku_is_rejected(client, db_session):
    organization = create_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        payload = product_payload()

        first = client.post("/products/", json=payload)
        assert first.status_code == 201

        second = client.post("/products/", json=payload)
        assert second.status_code == 400
        assert second.json()["detail"] == "Product SKU already exists."

    finally:
        app.dependency_overrides.clear()


# ============================================================
# READ TESTS
# ============================================================

def test_list_products_returns_only_own_organization(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    product1 = Product(
        organization_id=organization1.id,
        **product_payload("ORG1-SKU", "Org One Product"),
    )
    product2 = Product(
        organization_id=organization2.id,
        **product_payload("ORG2-SKU", "Org Two Product"),
    )

    db_session.add_all([product1, product2])
    db_session.flush()

    authenticate_as(UserRole.STAFF, organization1.id)

    try:
        response = client.get("/products/")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["sku"] == "ORG1-SKU"
        assert data[0]["organization_id"] == organization1.id

    finally:
        app.dependency_overrides.clear()


def test_get_product_by_id(client, db_session):
    organization = create_organization(db_session)

    product = Product(
        organization_id=organization.id,
        **product_payload(),
    )
    db_session.add(product)
    db_session.flush()

    authenticate_as(UserRole.STAFF, organization.id)

    try:
        response = client.get(f"/products/{product.id}")

        assert response.status_code == 200
        assert response.json()["id"] == product.id
        assert response.json()["sku"] == "SKU-001"

    finally:
        app.dependency_overrides.clear()


def test_cannot_get_another_organizations_product(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    product = Product(
        organization_id=organization1.id,
        **product_payload(),
    )
    db_session.add(product)
    db_session.flush()

    authenticate_as(UserRole.STAFF, organization2.id)

    try:
        response = client.get(f"/products/{product.id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found."

    finally:
        app.dependency_overrides.clear()


def test_product_pagination(client, db_session):
    organization = create_organization(db_session)

    for i in range(3):
        db_session.add(
            Product(
                organization_id=organization.id,
                **product_payload(
                    sku=f"PAGE-{i}",
                    name=f"Product {i}",
                ),
            )
        )

    db_session.flush()
    authenticate_as(UserRole.STAFF, organization.id)

    try:
        response = client.get("/products/?skip=1&limit=1")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["sku"] == "PAGE-1"

    finally:
        app.dependency_overrides.clear()


def test_product_pagination_rejects_invalid_limit(client):
    authenticate_as(UserRole.STAFF, 1)

    try:
        response = client.get("/products/?limit=0")
        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


# ============================================================
# UPDATE TESTS
# ============================================================

def test_owner_can_update_product(client, db_session):
    organization = create_organization(db_session)

    product = Product(
        organization_id=organization.id,
        **product_payload(),
    )
    db_session.add(product)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.put(
            f"/products/{product.id}",
            json={
                "name": "Updated Product",
                "price": "150.00",
            },
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Product"
        assert Decimal(str(response.json()["price"])) == Decimal("150.00")

        db_session.refresh(product)
        assert product.name == "Updated Product"

    finally:
        app.dependency_overrides.clear()


def test_cannot_update_another_organizations_product(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    product = Product(
        organization_id=organization1.id,
        **product_payload(),
    )
    db_session.add(product)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization2.id)

    try:
        response = client.put(
            f"/products/{product.id}",
            json={"name": "Unauthorized Update"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found."

        db_session.refresh(product)
        assert product.name == "Test Product"

    finally:
        app.dependency_overrides.clear()


# ============================================================
# DELETE TESTS
# ============================================================

def test_owner_can_delete_product(client, db_session):
    organization = create_organization(db_session)

    product = Product(
        organization_id=organization.id,
        **product_payload(),
    )
    db_session.add(product)
    db_session.flush()
    product_id = product.id

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.delete(f"/products/{product_id}")

        assert response.status_code == 204
        assert db_session.get(Product, product_id) is None

    finally:
        app.dependency_overrides.clear()


def test_cannot_delete_another_organizations_product(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    product = Product(
        organization_id=organization1.id,
        **product_payload(),
    )
    db_session.add(product)
    db_session.flush()
    product_id = product.id

    authenticate_as(UserRole.OWNER, organization2.id)

    try:
        response = client.delete(f"/products/{product_id}")

        assert response.status_code == 404
        assert db_session.get(Product, product_id) is not None

    finally:
        app.dependency_overrides.clear()