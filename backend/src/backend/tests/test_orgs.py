import pytest
from httpx import AsyncClient

from backend.models.org import Org
from backend.models.user import User


# ── Create org ────────────────────────────────────────────────────────────────
async def test_create_org(client: AsyncClient, test_user: User, auth_headers: dict):
    res = await client.post("/api/v1/orgs", json={"name": "My Org"}, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "My Org"
    assert data["slug"] == "my-org"
    assert data["plan"] == "free"


async def test_create_org_custom_slug(client: AsyncClient, auth_headers: dict):
    res = await client.post("/api/v1/orgs", json={
        "name": "My Org",
        "slug": "custom-slug",
    }, headers=auth_headers)
    assert res.status_code == 201
    assert res.json()["slug"] == "custom-slug"


async def test_create_org_duplicate_slug(
    client: AsyncClient, test_org: Org, auth_headers: dict
):
    # test_org already has slug "test-org"
    res = await client.post("/api/v1/orgs", json={"name": "Test Org"}, headers=auth_headers)
    assert res.status_code == 201
    # Should auto-increment slug to avoid collision
    assert res.json()["slug"] == "test-org-2"


async def test_create_org_unauthenticated(client: AsyncClient):
    res = await client.post("/api/v1/orgs", json={"name": "My Org"})
    assert res.status_code == 401


# ── List orgs ─────────────────────────────────────────────────────────────────
async def test_list_orgs(
    client: AsyncClient, test_org: Org, auth_headers: dict
):
    res = await client.get("/api/v1/orgs", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == str(test_org.id)
    assert data[0]["role"] == "owner"


async def test_list_orgs_empty(client: AsyncClient, test_user: User, auth_headers: dict):
    # test_user has no orgs (test_org fixture not used here)
    res = await client.get("/api/v1/orgs", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


# ── Get org ───────────────────────────────────────────────────────────────────
async def test_get_org(client: AsyncClient, test_org: Org, auth_headers: dict):
    res = await client.get(f"/api/v1/orgs/{test_org.id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == str(test_org.id)


async def test_get_org_not_member(
    client: AsyncClient, test_org: Org, auth_headers_2: dict
):
    # test_user_2 is not a member of test_org — should get 404 not 403
    res = await client.get(f"/api/v1/orgs/{test_org.id}", headers=auth_headers_2)
    assert res.status_code == 404


async def test_get_org_nonexistent(client: AsyncClient, auth_headers: dict):
    import uuid
    res = await client.get(f"/api/v1/orgs/{uuid.uuid4()}", headers=auth_headers)
    assert res.status_code == 404


# ── Update org ────────────────────────────────────────────────────────────────
async def test_update_org(client: AsyncClient, test_org: Org, auth_headers: dict):
    res = await client.patch(f"/api/v1/orgs/{test_org.id}", json={
        "name": "Updated Org Name",
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Org Name"


async def test_update_org_non_admin(
    client: AsyncClient,
    test_org: Org,
    test_user_2: User,
    auth_headers_2: dict,
    db,
):
    from backend.models.membership import Membership
    # Add test_user_2 as a regular member
    db.add(Membership(user_id=test_user_2.id, org_id=test_org.id, role="member"))
    await db.flush()

    res = await client.patch(f"/api/v1/orgs/{test_org.id}", json={
        "name": "Hacked Name",
    }, headers=auth_headers_2)
    assert res.status_code == 403


# ── Members ───────────────────────────────────────────────────────────────────
async def test_list_members(client: AsyncClient, test_org: Org, auth_headers: dict):
    res = await client.get(f"/api/v1/orgs/{test_org.id}/members", headers=auth_headers)
    assert res.status_code == 200
    members = res.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


async def test_remove_member(
    client: AsyncClient,
    test_org: Org,
    test_user: User,
    test_user_2: User,
    auth_headers: dict,
    db,
):
    from backend.models.membership import Membership
    db.add(Membership(user_id=test_user_2.id, org_id=test_org.id, role="member"))
    await db.flush()

    res = await client.delete(
        f"/api/v1/orgs/{test_org.id}/members/{test_user_2.id}",
        headers=auth_headers,
    )
    assert res.status_code == 204

    # Confirm member is gone
    members_res = await client.get(
        f"/api/v1/orgs/{test_org.id}/members", headers=auth_headers
    )
    assert len(members_res.json()) == 1


async def test_cannot_remove_owner(
    client: AsyncClient,
    test_org: Org,
    test_user: User,
    auth_headers: dict,
):
    res = await client.delete(
        f"/api/v1/orgs/{test_org.id}/members/{test_user.id}",
        headers=auth_headers,
    )
    assert res.status_code == 400