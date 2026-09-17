
from app.main import app
from app.api.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.warehouse import Warehouse


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


def create_organization(db_session, name="Warehouse Test Org"):
    organization = Organization(name=name)
    db_session.add(organization)
    db_session.flush()
    return organization


def warehouse_payload(name="Test Warehouse"):
    return {
        "name": name,
        "location": "Test Location",
    }


# ============================================================
# CREATE TESTS
# ============================================================

def test_owner_can_create_warehouse(client, db_session):
    organization = create_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.post(
            "/warehouses/",
            json=warehouse_payload(),
        )

        assert response.status_code == 201

        data = response.json()
        assert data["organization_id"] == organization.id
        assert data["name"] == "Test Warehouse"
        assert data["location"] == "Test Location"

        saved = db_session.get(Warehouse, data["id"])
        assert saved is not None
        assert saved.organization_id == organization.id

    finally:
        app.dependency_overrides.clear()


def test_duplicate_warehouse_name_is_rejected(
    client,
    db_session,
):
    organization = create_organization(db_session)
    authenticate_as(UserRole.OWNER, organization.id)

    try:
        payload = warehouse_payload()

        first = client.post("/warehouses/", json=payload)
        assert first.status_code == 201

        second = client.post("/warehouses/", json=payload)
        assert second.status_code == 400
        assert second.json()["detail"] == (
            "Warehouse name already exists."
        )

    finally:
        app.dependency_overrides.clear()


# ============================================================
# READ TESTS
# ============================================================

def test_list_warehouses_returns_only_own_organization(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    warehouse1 = Warehouse(
        organization_id=organization1.id,
        name="Warehouse One",
        location="Location One",
    )
    warehouse2 = Warehouse(
        organization_id=organization2.id,
        name="Warehouse Two",
        location="Location Two",
    )

    db_session.add_all([warehouse1, warehouse2])
    db_session.flush()

    authenticate_as(UserRole.STAFF, organization1.id)

    try:
        response = client.get("/warehouses/")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["name"] == "Warehouse One"
        assert data[0]["organization_id"] == organization1.id

    finally:
        app.dependency_overrides.clear()


def test_get_warehouse_by_id(client, db_session):
    organization = create_organization(db_session)

    warehouse = Warehouse(
        organization_id=organization.id,
        name="Main Warehouse",
        location="Chennai",
    )
    db_session.add(warehouse)
    db_session.flush()

    authenticate_as(UserRole.STAFF, organization.id)

    try:
        response = client.get(f"/warehouses/{warehouse.id}")

        assert response.status_code == 200
        assert response.json()["id"] == warehouse.id
        assert response.json()["name"] == "Main Warehouse"

    finally:
        app.dependency_overrides.clear()


def test_cannot_get_another_organizations_warehouse(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    warehouse = Warehouse(
        organization_id=organization1.id,
        name="Private Warehouse",
        location="Private Location",
    )
    db_session.add(warehouse)
    db_session.flush()

    authenticate_as(UserRole.STAFF, organization2.id)

    try:
        response = client.get(f"/warehouses/{warehouse.id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Warehouse not found."

    finally:
        app.dependency_overrides.clear()


def test_warehouse_pagination(client, db_session):
    organization = create_organization(db_session)

    for i in range(3):
        db_session.add(
            Warehouse(
                organization_id=organization.id,
                name=f"Warehouse {i}",
                location=f"Location {i}",
            )
        )

    db_session.flush()
    authenticate_as(UserRole.STAFF, organization.id)

    try:
        response = client.get("/warehouses/?skip=1&limit=1")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Warehouse 1"

    finally:
        app.dependency_overrides.clear()


def test_warehouse_pagination_rejects_invalid_limit(client):
    authenticate_as(UserRole.STAFF, 1)

    try:
        response = client.get("/warehouses/?limit=0")
        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


# ============================================================
# UPDATE TESTS
# ============================================================

def test_owner_can_update_warehouse(client, db_session):
    organization = create_organization(db_session)

    warehouse = Warehouse(
        organization_id=organization.id,
        name="Old Warehouse",
        location="Old Location",
    )
    db_session.add(warehouse)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.put(
            f"/warehouses/{warehouse.id}",
            json={
                "name": "Updated Warehouse",
                "location": "New Location",
            },
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Warehouse"
        assert response.json()["location"] == "New Location"

        db_session.refresh(warehouse)
        assert warehouse.name == "Updated Warehouse"

    finally:
        app.dependency_overrides.clear()


def test_cannot_update_another_organizations_warehouse(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    warehouse = Warehouse(
        organization_id=organization1.id,
        name="Private Warehouse",
        location="Private Location",
    )
    db_session.add(warehouse)
    db_session.flush()

    authenticate_as(UserRole.OWNER, organization2.id)

    try:
        response = client.put(
            f"/warehouses/{warehouse.id}",
            json={"name": "Unauthorized Update"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Warehouse not found."

        db_session.refresh(warehouse)
        assert warehouse.name == "Private Warehouse"

    finally:
        app.dependency_overrides.clear()


# ============================================================
# DELETE TESTS
# ============================================================

def test_owner_can_delete_warehouse(client, db_session):
    organization = create_organization(db_session)

    warehouse = Warehouse(
        organization_id=organization.id,
        name="Delete Warehouse",
        location="Test Location",
    )
    db_session.add(warehouse)
    db_session.flush()
    warehouse_id = warehouse.id

    authenticate_as(UserRole.OWNER, organization.id)

    try:
        response = client.delete(
            f"/warehouses/{warehouse_id}"
        )

        assert response.status_code == 204
        assert db_session.get(Warehouse, warehouse_id) is None

    finally:
        app.dependency_overrides.clear()


def test_cannot_delete_another_organizations_warehouse(
    client,
    db_session,
):
    organization1 = create_organization(db_session, "Org One")
    organization2 = create_organization(db_session, "Org Two")

    warehouse = Warehouse(
        organization_id=organization1.id,
        name="Private Warehouse",
        location="Private Location",
    )
    db_session.add(warehouse)
    db_session.flush()
    warehouse_id = warehouse.id

    authenticate_as(UserRole.OWNER, organization2.id)

    try:
        response = client.delete(
            f"/warehouses/{warehouse_id}"
        )

        assert response.status_code == 404
        assert db_session.get(Warehouse, warehouse_id) is not None

    finally:
        app.dependency_overrides.clear()