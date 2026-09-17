
import pytest

from app.main import app
from app.api.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User, UserRole


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def fake_user(role: UserRole, organization_id: int) -> User:
    return User(
        id=999,
        name="Test User",
        email="testuser@example.com",
        password_hash="fake-password",
        role=role,
        organization_id=organization_id,
        is_active=True,
    )


def authenticate_as(role: UserRole, organization_id: int):
    app.dependency_overrides[get_current_user] = lambda: fake_user(
        role,
        organization_id,
    )


def create_test_organization(db_session):
    organization = Organization(
        name="Customer Test Organization",
    )
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    return organization


def create_customer(client, name="Test Customer", **kwargs):
    payload = {"name": name, **kwargs}
    return client.post("/customers/", json=payload)


# --------------------------------------------------
# CREATE CUSTOMER
# --------------------------------------------------

def test_create_customer_success(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_customer(
            client,
            name="ABC Company",
            email="abc@example.com",
            phone="9876543210",
            address="Chennai",
        )

        assert response.status_code in (200, 201), response.text

        data = response.json()
        assert data["name"] == "ABC Company"
        assert data["email"] == "abc@example.com"
        assert data["phone"] == "9876543210"
        assert data["address"] == "Chennai"
        assert data["organization_id"] == organization.id
        assert "id" in data
    finally:
        app.dependency_overrides.clear()


def test_create_customer_with_only_required_fields(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_customer(client, name="Minimal Customer")

        assert response.status_code in (200, 201), response.text

        data = response.json()
        assert data["name"] == "Minimal Customer"
        assert data["organization_id"] == organization.id
    finally:
        app.dependency_overrides.clear()


def test_create_customer_missing_name(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.post(
            "/customers/",
            json={"email": "missingname@example.com"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_create_customer_empty_name(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_customer(client, name="")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_create_customer_name_too_long(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_customer(client, name="A" * 151)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_create_customer_email_too_long(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = create_customer(
            client,
            name="Long Email Customer",
            email="a" * 250 + "@example.com",
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# --------------------------------------------------
# LIST CUSTOMERS
# --------------------------------------------------

def test_list_customers(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        create_customer(client, name="Customer One")
        create_customer(client, name="Customer Two")

        response = client.get("/customers/")

        assert response.status_code == 200, response.text

        data = response.json()
        assert len(data) == 2
        assert {item["name"] for item in data} == {
            "Customer One",
            "Customer Two",
        }
    finally:
        app.dependency_overrides.clear()


def test_list_customers_empty(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.get("/customers/")

        assert response.status_code == 200, response.text
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_customers_pagination(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        for name in ("Customer One", "Customer Two", "Customer Three"):
            create_customer(client, name=name)

        response = client.get("/customers/?skip=0&limit=2")

        assert response.status_code == 200, response.text
        assert len(response.json()) == 2
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "query",
    [
        "?skip=-1",
        "?limit=0",
        "?limit=101",
    ],
)
def test_list_customers_invalid_pagination(client, db_session, query):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.get(f"/customers/{query}")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_list_customers_tenant_isolation(client, db_session):
    org_one = create_test_organization(db_session)

    org_two = Organization(name="Another Organization")
    db_session.add(org_two)
    db_session.commit()
    db_session.refresh(org_two)

    authenticate_as(UserRole.OWNER, org_one.id)

    try:
        first = create_customer(client, name="Organization One Customer")
        assert first.status_code in (200, 201), first.text

        authenticate_as(UserRole.OWNER, org_two.id)

        second = create_customer(client, name="Organization Two Customer")
        assert second.status_code in (200, 201), second.text

        response = client.get("/customers/")

        assert response.status_code == 200, response.text
        data = response.json()

        assert len(data) == 1
        assert data[0]["name"] == "Organization Two Customer"
        assert data[0]["organization_id"] == org_two.id
    finally:
        app.dependency_overrides.clear()


# --------------------------------------------------
# GET CUSTOMER
# --------------------------------------------------

def test_get_customer_success(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        created = create_customer(client, name="Customer To Retrieve")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]
        response = client.get(f"/customers/{customer_id}")

        assert response.status_code == 200, response.text
        assert response.json()["name"] == "Customer To Retrieve"
    finally:
        app.dependency_overrides.clear()


def test_get_customer_not_found(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.get("/customers/999999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_get_customer_other_tenant_not_found(client, db_session):
    org_one = create_test_organization(db_session)

    org_two = Organization(name="Second Organization")
    db_session.add(org_two)
    db_session.commit()
    db_session.refresh(org_two)

    authenticate_as(UserRole.OWNER, org_one.id)

    try:
        created = create_customer(client, name="Private Customer")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]
        authenticate_as(UserRole.OWNER, org_two.id)

        response = client.get(f"/customers/{customer_id}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# --------------------------------------------------
# UPDATE CUSTOMER
# --------------------------------------------------

def test_update_customer_success(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        created = create_customer(
            client,
            name="Original Customer",
            email="original@example.com",
        )
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]

        response = client.put(
            f"/customers/{customer_id}",
            json={
                "name": "Updated Customer",
                "phone": "9876543210",
            },
        )

        assert response.status_code == 200, response.text

        data = response.json()
        assert data["name"] == "Updated Customer"
        assert data["phone"] == "9876543210"
        assert data["email"] == "original@example.com"
    finally:
        app.dependency_overrides.clear()


def test_update_customer_partial_update(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        created = create_customer(
            client,
            name="Partial Update Customer",
            email="partial@example.com",
        )
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]

        response = client.put(
            f"/customers/{customer_id}",
            json={"phone": "1234567890"},
        )

        assert response.status_code == 200, response.text

        data = response.json()
        assert data["name"] == "Partial Update Customer"
        assert data["email"] == "partial@example.com"
        assert data["phone"] == "1234567890"
    finally:
        app.dependency_overrides.clear()


def test_update_customer_not_found(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.put(
            "/customers/999999",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_update_customer_other_tenant_not_found(client, db_session):
    org_one = create_test_organization(db_session)

    org_two = Organization(name="Another Organization")
    db_session.add(org_two)
    db_session.commit()
    db_session.refresh(org_two)

    authenticate_as(UserRole.OWNER, org_one.id)

    try:
        created = create_customer(client, name="Tenant One Customer")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]
        authenticate_as(UserRole.OWNER, org_two.id)

        response = client.put(
            f"/customers/{customer_id}",
            json={"name": "Unauthorized Update"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_update_customer_empty_name(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        created = create_customer(client, name="Valid Customer")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]

        response = client.put(
            f"/customers/{customer_id}",
            json={"name": ""},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# --------------------------------------------------
# DELETE CUSTOMER
# --------------------------------------------------

def test_delete_customer_success(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        created = create_customer(client, name="Customer To Delete")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]

        response = client.delete(f"/customers/{customer_id}")
        assert response.status_code in (200, 204), response.text

        get_response = client.get(f"/customers/{customer_id}")
        assert get_response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_delete_customer_not_found(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.delete("/customers/999999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_delete_customer_other_tenant_not_found(client, db_session):
    org_one = create_test_organization(db_session)

    org_two = Organization(name="Second Organization")
    db_session.add(org_two)
    db_session.commit()
    db_session.refresh(org_two)

    authenticate_as(UserRole.OWNER, org_one.id)

    try:
        created = create_customer(client, name="Tenant One Customer")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]
        authenticate_as(UserRole.OWNER, org_two.id)

        response = client.delete(f"/customers/{customer_id}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# --------------------------------------------------
# ROLE-BASED ACCESS CONTROL
# --------------------------------------------------

@pytest.mark.parametrize(
    "role",
    [
        UserRole.OWNER,
        UserRole.ADMIN,
        UserRole.MANAGER,
    ],
)
def test_allowed_roles_can_create_customer(client, db_session, role):
    organization = create_test_organization(db_session)
    authenticate_as(role, organization.id)

    try:
        response = create_customer(client, name="RBAC Allowed Customer")
        assert response.status_code in (200, 201), response.text
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_create_customer(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.STAFF, organization.id)

    try:
        response = create_customer(client, name="Restricted Customer")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_update_customer(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        created = create_customer(client, name="Customer For RBAC Update")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]
        authenticate_as(UserRole.STAFF, organization.id)

        response = client.put(
            f"/customers/{customer_id}",
            json={"name": "Unauthorized Update"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_staff_cannot_delete_customer(client, db_session):
    organization = create_test_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        created = create_customer(client, name="Customer For RBAC Delete")
        assert created.status_code in (200, 201), created.text

        customer_id = created.json()["id"]
        authenticate_as(UserRole.STAFF, organization.id)

        response = client.delete(f"/customers/{customer_id}")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()