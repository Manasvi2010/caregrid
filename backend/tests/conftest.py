import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def _login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="session")
def nurse_headers(client):
    return _login(client, "nurse@caregrid.com", "nurse123")


@pytest.fixture(scope="session")
def admin_headers(client):
    return _login(client, "admin@caregrid.com", "admin123")