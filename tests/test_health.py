
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_app_starts():
    response = client.get("/")

    # The root endpoint may not exist yet.
    assert response.status_code in (200, 404)