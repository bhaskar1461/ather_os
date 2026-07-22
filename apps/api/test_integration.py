"""
Comprehensive integration tests covering auth flow, user endpoints,
and workspace/project CRUD with proper UUID handling.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from app.security.dependencies import get_current_user
from packages.database.models import User
from packages.database.connection import Base, engine


# ── Create all tables before tests ────────────────────────────────────────────
Base.metadata.create_all(bind=engine)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_TEST_USER_ID = uuid.uuid4()


class MockUser:
    """Mimic a real User ORM object with a proper UUID id."""
    id = _TEST_USER_ID
    email = "integration@example.com"
    name = "Test User"
    avatar_url = None
    role = "user"
    is_verified = True
    created_at = datetime(2025, 1, 1)
    updated_at = datetime(2025, 1, 1)


async def override_get_current_user():
    return MockUser()


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


# ── System ────────────────────────────────────────────────────────────────────

def test_health():
    """Health endpoint should always return 200."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert "version" in data
    assert "database" in data
    assert "redis" in data


def test_openapi_docs():
    """OpenAPI spec should be reachable."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data


# ── Workspaces ────────────────────────────────────────────────────────────────

def test_workspace_crud():
    """Create, list, get, and delete a workspace."""
    # List (auto-creates a default workspace)
    resp = client.get("/workspaces")
    assert resp.status_code == 200
    workspaces = resp.json()
    assert len(workspaces) >= 1
    ws_id = workspaces[0]["id"]

    # Get by ID
    resp = client.get(f"/workspaces/{ws_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == ws_id

    # Create a new workspace
    resp = client.post(
        "/workspaces",
        json={"name": "Test WS", "description": "Integration test workspace"},
    )
    assert resp.status_code == 201
    new_ws = resp.json()
    new_ws_id = new_ws["id"]
    assert new_ws["name"] == "Test WS"

    # Delete the new workspace
    resp = client.delete(f"/workspaces/{new_ws_id}")
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()


def test_workspace_not_found():
    """Requesting a non-existent workspace should return 404."""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/workspaces/{fake_id}")
    assert resp.status_code == 404


# ── Projects ──────────────────────────────────────────────────────────────────

def test_project_crud():
    """Create and list projects within a workspace."""
    # Get a workspace first
    resp = client.get("/workspaces")
    ws_id = resp.json()[0]["id"]

    # List projects (auto-creates a default project)
    resp = client.get(f"/workspaces/{ws_id}/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 1

    # Create a new project
    resp = client.post(
        f"/workspaces/{ws_id}/projects",
        json={"name": "Test Project", "description": "An integration test project"},
    )
    assert resp.status_code == 201
    proj = resp.json()
    assert proj["name"] == "Test Project"

    # Delete the project
    resp = client.delete(f"/workspaces/{ws_id}/projects/{proj['id']}")
    assert resp.status_code == 200


# ── Invalid UUID ──────────────────────────────────────────────────────────────

def test_invalid_uuid_returns_422():
    """Passing a non-UUID string should return a 422 validation error."""
    resp = client.get("/workspaces/not-a-uuid")
    assert resp.status_code == 422


# ── Astrology Compatibility ──────────────────────────────────────────────────

def test_compatibility():
    """Compatibility endpoint should return a valid score."""
    payload = {
        "partner_a": {
            "year": 1990, "month": 5, "day": 15, "hour": 10, "minute": 30,
            "location_name": "Mumbai, India",
            "location_lat": 19.076, "location_lon": 72.877,
            "location_timezone": "Asia/Kolkata",
        },
        "partner_b": {
            "year": 1992, "month": 8, "day": 20, "hour": 14, "minute": 15,
            "location_name": "Delhi, India",
            "location_lat": 28.613, "location_lon": 77.209,
            "location_timezone": "Asia/Kolkata",
        },
        "partner_a_name": "Groom A",
        "partner_b_name": "Bride B",
        "force_refresh": True,
    }
    resp = client.post("/astrology/compatibility", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert 0 <= data["score"] <= 36


def test_transit():
    """Transit endpoint should return horoscope data."""
    payload = {
        "birth_year": 1990, "birth_month": 5, "birth_day": 15,
        "birth_hour": 10, "birth_minute": 30,
        "birth_lat": 19.076, "birth_lon": 72.877,
        "birth_timezone": "Asia/Kolkata",
        "current_lat": 19.076, "current_lon": 72.877,
        "current_timezone": "Asia/Kolkata",
        "force_refresh": True,
    }
    resp = client.post("/astrology/transit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "horoscope" in data
    assert "date" in data
