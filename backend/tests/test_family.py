"""
Integration tests for Family & Invitation endpoints (Phase 3).
Uses in-memory SQLite via conftest.py fixtures.
Each test function gets a fresh, isolated database.

Covers:
- Family CRUD lifecycle
- Invitation creation, join, list, cancel
- Edge cases: expiry, seat limit, re-join, spam, validation
"""

import pytest
from httpx import AsyncClient


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

async def _register(client: AsyncClient, email: str, role: str, name: str = "Test User"):
    res = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Secret123",
        "full_name": name,
        "role": role,
    })
    assert res.status_code == 201, res.text
    return res.json()["data"]


async def _login(client: AsyncClient, email: str) -> dict:
    res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Secret123",
    })
    assert res.status_code == 200, res.text
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
async def parent_headers(client: AsyncClient):
    await _register(client, "parent@test.com", "parent", "Bapak Budi")
    return await _login(client, "parent@test.com")


@pytest.fixture
async def child_headers(client: AsyncClient):
    await _register(client, "child@test.com", "child", "Anak Riri")
    return await _login(client, "child@test.com")


@pytest.fixture
async def family_with_invite(client: AsyncClient, parent_headers):
    """Create a family and return invite code."""
    res = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Budi"},
        headers=parent_headers,
    )
    assert res.status_code == 201, res.text

    inv_res = await client.post(
        "/api/v1/invitations/",
        json={"invitee_name": "Anak Riri"},
        headers=parent_headers,
    )
    assert inv_res.status_code == 201, inv_res.text
    return {
        "family": res.json()["data"],
        "invitation": inv_res.json()["data"],
        "invite_code": inv_res.json()["data"]["invite_code"],
    }


# ================================================================== #
# 3.1 — Create Family
# ================================================================== #

@pytest.mark.asyncio
async def test_create_family_success(client: AsyncClient, parent_headers):
    response = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Santoso"},
        headers=parent_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Keluarga Santoso"
    assert data["max_seats"] == 2


@pytest.mark.asyncio
async def test_child_cannot_create_family(client: AsyncClient, child_headers):
    response = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Anak"},
        headers=child_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_parent_cannot_create_second_family(client: AsyncClient, parent_headers):
    await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Pertama"},
        headers=parent_headers,
    )
    response = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Kedua"},
        headers=parent_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FAMILY_EXISTS"


@pytest.mark.asyncio
async def test_create_family_unauthenticated_returns_401(client: AsyncClient):
    response = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga X"},
    )
    assert response.status_code == 401


# T7: Create family with whitespace-only name
@pytest.mark.asyncio
async def test_create_family_whitespace_name_returns_422(client: AsyncClient, parent_headers):
    """Name with only whitespace should be rejected by min_length=2 after strip."""
    response = await client.post(
        "/api/v1/families/",
        json={"name": " "},
        headers=parent_headers,
    )
    assert response.status_code == 422


# ================================================================== #
# 3.2 — Get My Family
# ================================================================== #

@pytest.mark.asyncio
async def test_get_my_family(client: AsyncClient, parent_headers):
    await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Santoso"},
        headers=parent_headers,
    )
    response = await client.get("/api/v1/families/me", headers=parent_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Keluarga Santoso"
    assert data["member_count"] == 1
    assert len(data["members"]) == 1


@pytest.mark.asyncio
async def test_get_family_without_family_returns_404(client: AsyncClient, parent_headers):
    response = await client.get("/api/v1/families/me", headers=parent_headers)
    assert response.status_code == 404


# T8: Non-member tries to list family members
@pytest.mark.asyncio
async def test_non_member_cannot_list_members(client: AsyncClient, parent_headers):
    """Parent not in any family tries to list members of a random family_id."""
    import uuid
    fake_id = str(uuid.uuid4())
    # First create a family so parent IS in a family but different one
    await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Budi"},
        headers=parent_headers,
    )
    # Register another parent with another family
    await _register(client, "parent2@test.com", "parent", "Bapak Andi")
    parent2_headers = await _login(client, "parent2@test.com")
    res2 = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Andi"},
        headers=parent2_headers,
    )
    family2_id = res2.json()["data"]["id"]

    # Parent 1 tries to list members of family 2
    response = await client.get(
        f"/api/v1/families/{family2_id}/members",
        headers=parent_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_FAMILY_MEMBER"


# ================================================================== #
# 3.3 — Invitations
# ================================================================== #

@pytest.mark.asyncio
async def test_create_invitation_success(client: AsyncClient, parent_headers):
    await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Budi"},
        headers=parent_headers,
    )
    response = await client.post(
        "/api/v1/invitations/",
        json={"invitee_name": "Anak Budi"},
        headers=parent_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["invite_code"]) == 6
    assert data["invite_code"].isdigit()
    assert data["status"] == "sent"


@pytest.mark.asyncio
async def test_child_cannot_create_invitation(client: AsyncClient, child_headers):
    response = await client.post(
        "/api/v1/invitations/",
        json={},
        headers=child_headers,
    )
    assert response.status_code == 403


# M3: Non-digit invite code should be rejected at schema level
@pytest.mark.asyncio
async def test_join_with_non_digit_code_returns_422(client: AsyncClient, child_headers):
    """invite_code='abcdef' should be rejected by digit-only validator."""
    response = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": "abcdef"},
        headers=child_headers,
    )
    assert response.status_code == 422


# ================================================================== #
# 3.4 — Join Family
# ================================================================== #

@pytest.mark.asyncio
async def test_child_joins_family_success(
    client: AsyncClient, child_headers, family_with_invite
):
    invite_code = family_with_invite["invite_code"]
    response = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["member_count"] == 2
    assert any(m["role"] == "member" for m in data["members"])


@pytest.mark.asyncio
async def test_join_with_invalid_code_returns_404(client: AsyncClient, child_headers):
    response = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": "000000"},
        headers=child_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_join_used_code_returns_409(
    client: AsyncClient, child_headers, family_with_invite
):
    """Second child cannot use the same invite code."""
    await _register(client, "child2@test.com", "child", "Anak Kedua")
    child2_headers = await _login(client, "child2@test.com")

    invite_code = family_with_invite["invite_code"]
    # First child joins
    await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )
    # Second child tries same code
    response = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child2_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_already_member_cannot_join_again(
    client: AsyncClient, child_headers, family_with_invite
):
    """Child already in a family cannot join another."""
    invite_code = family_with_invite["invite_code"]
    await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )

    # Create another parent + family + invitation
    await _register(client, "parent2@test.com", "parent", "Bapak Dudi")
    parent2_headers = await _login(client, "parent2@test.com")
    await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Dudi"},
        headers=parent2_headers,
    )
    inv2 = await client.post(
        "/api/v1/invitations/",
        json={},
        headers=parent2_headers,
    )
    code2 = inv2.json()["data"]["invite_code"]

    response = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": code2},
        headers=child_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_MEMBER"


@pytest.mark.asyncio
async def test_parent_cannot_join_family(
    client: AsyncClient, parent_headers, family_with_invite
):
    """Parent role cannot use /join endpoint (child only)."""
    invite_code = family_with_invite["invite_code"]
    response = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=parent_headers,
    )
    assert response.status_code == 403


# T1: Expired invitation (manipulate expires_at in DB)
@pytest.mark.asyncio
async def test_join_expired_invitation_returns_410(
    client: AsyncClient, child_headers, family_with_invite
):
    """Join with an expired invitation should return 410."""
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import update
    from app.models.invitation import Invitation
    from app.database import get_db

    invite_code = family_with_invite["invite_code"]

    # Manually expire the invitation by setting expires_at to the past
    # We need access to the DB session — use the app's dependency
    from app.main import create_app
    # Access the test DB via internal route trick: call the service directly
    # Instead, make it expired via the test db fixture
    # The conftest db fixture is session-scoped, so we use a raw approach:

    # Actually, the cleanest way is to call the endpoint and check.
    # But since we can't manipulate the DB from the test directly without
    # the db fixture, let's use a different approach:
    # We'll monkeypatch datetime.now to simulate time passing.

    import unittest.mock
    # Set "now" to 25 hours in the future so the 24h invitation is expired
    future_time = datetime.now(UTC) + timedelta(hours=25)

    with unittest.mock.patch(
        "app.services.invitation_service.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = future_time
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        # Need UTC constant too
        from datetime import UTC as _utc
        response = await client.post(
            "/api/v1/invitations/join",
            json={"invite_code": invite_code},
            headers=child_headers,
        )

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "INVITATION_EXPIRED"


# T3: Seat limit reached — join when family full
@pytest.mark.asyncio
async def test_join_when_family_full_returns_400(
    client: AsyncClient, parent_headers, child_headers, family_with_invite
):
    """When family is at max capacity, new join should fail."""
    invite_code = family_with_invite["invite_code"]

    # Child joins → family becomes 2/2 (full for FREE tier)
    res = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )
    assert res.status_code == 200

    # Create a new invitation (should fail because family is now full)
    inv_res = await client.post(
        "/api/v1/invitations/",
        json={"invitee_name": "Another Child"},
        headers=parent_headers,
    )
    assert inv_res.status_code == 400
    assert inv_res.json()["error"]["code"] == "SEAT_LIMIT_REACHED"


# T4: Child removed then re-joins same family
@pytest.mark.asyncio
async def test_removed_child_can_rejoin_family(
    client: AsyncClient, parent_headers, child_headers, family_with_invite
):
    """After being removed, a child should be able to rejoin via a new invite."""
    invite_code = family_with_invite["invite_code"]
    family_id = family_with_invite["family"]["id"]

    # Child joins
    await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )

    # Get child user id
    child_me = await client.get("/api/v1/users/me", headers=child_headers)
    child_id = child_me.json()["data"]["id"]

    # Parent removes child
    await client.delete(
        f"/api/v1/families/{family_id}/members/{child_id}",
        headers=parent_headers,
    )

    # Parent creates new invitation
    new_inv = await client.post(
        "/api/v1/invitations/",
        json={"invitee_name": "Anak Riri lagi"},
        headers=parent_headers,
    )
    assert new_inv.status_code == 201
    new_code = new_inv.json()["data"]["invite_code"]

    # Child re-joins
    rejoin_res = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": new_code},
        headers=child_headers,
    )
    assert rejoin_res.status_code == 200
    assert rejoin_res.json()["data"]["member_count"] == 2


# T5: Cancel invitation that is already accepted
@pytest.mark.asyncio
async def test_cancel_already_accepted_invitation_returns_403(
    client: AsyncClient, parent_headers, child_headers, family_with_invite
):
    """Cannot cancel an already-accepted invitation."""
    invite_code = family_with_invite["invite_code"]
    invitation_id = family_with_invite["invitation"]["id"]

    # Child joins (accepts the invitation)
    await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )

    # Try to cancel the now-accepted invitation
    response = await client.delete(
        f"/api/v1/invitations/{invitation_id}",
        headers=parent_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVITATION_NOT_CANCELLABLE"


# T6: Remove non-existent member (random UUID)
@pytest.mark.asyncio
async def test_remove_nonexistent_member_returns_404(
    client: AsyncClient, parent_headers
):
    """Removing a member with a random UUID should return 404."""
    import uuid
    await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Test"},
        headers=parent_headers,
    )
    family_res = await client.get("/api/v1/families/me", headers=parent_headers)
    family_id = family_res.json()["data"]["id"]
    fake_user_id = str(uuid.uuid4())

    response = await client.delete(
        f"/api/v1/families/{family_id}/members/{fake_user_id}",
        headers=parent_headers,
    )
    assert response.status_code == 404


# ================================================================== #
# 3.5 — Remove Member
# ================================================================== #

@pytest.mark.asyncio
async def test_remove_member_success(
    client: AsyncClient, parent_headers, child_headers, family_with_invite
):
    invite_code = family_with_invite["invite_code"]
    family_id = family_with_invite["family"]["id"]

    # Child joins
    await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )

    child_me = await client.get("/api/v1/users/me", headers=child_headers)
    child_id = child_me.json()["data"]["id"]

    # Parent removes child
    response = await client.delete(
        f"/api/v1/families/{family_id}/members/{child_id}",
        headers=parent_headers,
    )
    assert response.status_code == 204

    # Verify family now has 1 member
    family_res = await client.get("/api/v1/families/me", headers=parent_headers)
    assert family_res.json()["data"]["member_count"] == 1


@pytest.mark.asyncio
async def test_parent_cannot_remove_self(
    client: AsyncClient, parent_headers
):
    await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Solo"},
        headers=parent_headers,
    )
    me = await client.get("/api/v1/users/me", headers=parent_headers)
    parent_id = me.json()["data"]["id"]
    family_res = await client.get("/api/v1/families/me", headers=parent_headers)
    family_id = family_res.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/families/{family_id}/members/{parent_id}",
        headers=parent_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CANNOT_REMOVE_SELF"


# ================================================================== #
# 3.6 — List & Cancel Invitations
# ================================================================== #

@pytest.mark.asyncio
async def test_list_invitations(client: AsyncClient, parent_headers, family_with_invite):
    response = await client.get("/api/v1/invitations/family", headers=parent_headers)
    assert response.status_code == 200
    invitations = response.json()["data"]
    assert len(invitations) >= 1


@pytest.mark.asyncio
async def test_cancel_invitation(
    client: AsyncClient, parent_headers, child_headers, family_with_invite
):
    invitation_id = family_with_invite["invitation"]["id"]
    response = await client.delete(
        f"/api/v1/invitations/{invitation_id}",
        headers=parent_headers,
    )
    assert response.status_code == 204

    # Cancelled code should be rejected when child tries to use it
    response2 = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": family_with_invite["invite_code"]},
        headers=child_headers,
    )
    assert response2.status_code == 410
    assert response2.json()["error"]["code"] == "INVITATION_CANCELLED"
