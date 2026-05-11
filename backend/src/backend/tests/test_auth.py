import pytest
from httpx import AsyncClient

from backend.models.user import User


# ── Register ──────────────────────────────────────────────────────────────────
async def test_register_success(client: AsyncClient):
    res = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "password123",
        "full_name": "New User",
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["full_name"] == "New User"
    assert "hashed_password" not in data["user"]


async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    res = await client.post("/api/v1/auth/register", json={
        "email": test_user.email,
        "password": "password123",
    })
    assert res.status_code == 409


async def test_register_weak_password(client: AsyncClient):
    res = await client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "123",
    })
    assert res.status_code == 422


async def test_register_invalid_email(client: AsyncClient):
    res = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "password": "password123",
    })
    assert res.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────
async def test_login_success(client: AsyncClient, test_user: User):
    res = await client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "password123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user.email


async def test_login_wrong_password(client: AsyncClient, test_user: User):
    res = await client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "wrongpassword",
    })
    assert res.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    res = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123",
    })
    assert res.status_code == 401
    # Make sure we don't leak whether the email exists
    assert res.json()["detail"] == "Invalid email or password"


# ── Me ────────────────────────────────────────────────────────────────────────
async def test_me_authenticated(client: AsyncClient, test_user: User, auth_headers: dict):
    res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name


async def test_me_unauthenticated(client: AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


async def test_me_invalid_token(client: AsyncClient):
    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer notavalidtoken"}
    )
    assert res.status_code == 401


# ── Refresh ───────────────────────────────────────────────────────────────────
async def test_refresh_success(client: AsyncClient, test_user: User):
    # Login to get a real refresh token
    login_res = await client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "password123",
    })
    refresh_token = login_res.json()["refresh_token"]

    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user.email


async def test_refresh_invalid_token(client: AsyncClient):
    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "notavalidtoken",
    })
    assert res.status_code == 401


# ── Update profile ────────────────────────────────────────────────────────────
async def test_update_profile(client: AsyncClient, test_user: User, auth_headers: dict):
    res = await client.patch("/api/v1/auth/me", json={
        "full_name": "Updated Name",
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["full_name"] == "Updated Name"


async def test_update_profile_unauthenticated(client: AsyncClient):
    res = await client.patch("/api/v1/auth/me", json={"full_name": "Hacker"})
    assert res.status_code == 401