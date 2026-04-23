"""
Integration tests for Phase 6 Engagement Features.
Covers: Savings Goals, Notifications, Subscriptions.
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
    await _register(client, "parent1@test.com", "parent", "Bapak Engagement")
    return await _login(client, "parent1@test.com")

@pytest.fixture
async def child_headers(client: AsyncClient):
    await _register(client, "child1@test.com", "child", "Anak Engagement")
    return await _login(client, "child1@test.com")

@pytest.fixture
async def family_setup(client: AsyncClient, parent_headers, child_headers):
    # Create family
    res = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Engagement"},
        headers=parent_headers,
    )
    assert res.status_code == 201, res.text
    family_id = res.json()["data"]["id"]

    # Parent invites child
    inv_res = await client.post(
        "/api/v1/invitations/",
        json={"invitee_name": "Anak Engagement"},
        headers=parent_headers,
    )
    assert inv_res.status_code == 201, inv_res.text
    invite_code = inv_res.json()["data"]["invite_code"]

    # Child accepts
    acc_res = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )
    assert acc_res.status_code == 200, acc_res.text
    return {"family_id": family_id}


# ================================================================== #
# Savings Goals
# ================================================================== #

@pytest.mark.asyncio
async def test_savings_goals_full_lifecycle(client: AsyncClient, family_setup, parent_headers, child_headers):
    """Test: create goal, contribute twice to complete, verify milestones."""
    me_resp = await client.get("/api/v1/users/me", headers=child_headers)
    child_id = me_resp.json()["data"]["id"]

    # Parent create allowance + topup wallet + transfer
    alw_res = await client.post(
        "/api/v1/allowances/",
        json={
            "child_id": child_id,
            "amount": 100000.00,
            "currency": "IDR",
            "is_recurring": False
        },
        headers=parent_headers,
    )
    assert alw_res.status_code == 201, alw_res.text
    allowance_id = alw_res.json()["data"]["id"]

    topup_res = await client.post(
        "/api/v1/wallets/topup",
        json={"amount": "500000.00", "description": "test topup"},
        headers=parent_headers,
    )
    assert topup_res.status_code == 200, topup_res.text

    trf_res = await client.post(
        f"/api/v1/allowances/{allowance_id}/transfer",
        headers=parent_headers,
    )
    assert trf_res.status_code == 200, trf_res.text

    # Child creates savings goal
    sg_res = await client.post(
        "/api/v1/savings-goals",
        json={"name": "Beli Mainan", "target_amount": 50000.00},
        headers=child_headers,
    )
    assert sg_res.status_code == 201, sg_res.text
    goal_id = sg_res.json()["id"]

    # First contribution (50%)
    ct_res = await client.post(
        f"/api/v1/savings-goals/{goal_id}/contribute",
        json={"amount": 25000.00},
        headers=child_headers,
    )
    assert ct_res.status_code == 200, ct_res.text
    assert float(ct_res.json()["current_amount"]) == 25000.0

    # Second contribution to reach 100%
    ct2_res = await client.post(
        f"/api/v1/savings-goals/{goal_id}/contribute",
        json={"amount": 25000.00},
        headers=child_headers,
    )
    assert ct2_res.status_code == 200, ct2_res.text
    assert ct2_res.json()["is_completed"] is True
    assert float(ct2_res.json()["current_amount"]) == 50000.0

    # Cannot contribute to completed goal
    ct3_res = await client.post(
        f"/api/v1/savings-goals/{goal_id}/contribute",
        json={"amount": 1000.00},
        headers=child_headers,
    )
    assert ct3_res.status_code == 400


@pytest.mark.asyncio
async def test_parent_cannot_create_savings_goal(client: AsyncClient, family_setup, parent_headers):
    """Parent role should be forbidden from creating savings goals."""
    res = await client.post(
        "/api/v1/savings-goals",
        json={"name": "Goal Parent", "target_amount": 10000.00},
        headers=parent_headers,
    )
    assert res.status_code == 403


# ================================================================== #
# Notifications
# ================================================================== #

@pytest.mark.asyncio
async def test_notifications_lifecycle(client: AsyncClient, family_setup, parent_headers, child_headers):
    """Test: trigger notification via task submit, read, mark-all-read."""
    me_resp = await client.get("/api/v1/users/me", headers=child_headers)
    child_id = me_resp.json()["data"]["id"]

    # Create task and child submits
    tsk_res = await client.post(
        "/api/v1/tasks/",
        json={
            "assigned_to": child_id,
            "title": "Cuci Piring",
            "reward_amount": 10000.00,
            "reward_currency": "IDR",
            "is_recurring": False
        },
        headers=parent_headers,
    )
    assert tsk_res.status_code == 201, tsk_res.text
    task_id = tsk_res.json()["data"]["id"]

    sub_res = await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers=child_headers,
    )
    assert sub_res.status_code == 200, sub_res.text

    # Parent checks notifications (page-based pagination)
    ntf_res = await client.get("/api/v1/notifications?page=1&per_page=20", headers=parent_headers)
    assert ntf_res.status_code == 200, ntf_res.text
    notifications = ntf_res.json()
    assert len(notifications) > 0

    # Read first notification
    notif_id = notifications[0]["id"]
    rd_res = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=parent_headers)
    assert rd_res.status_code == 200, rd_res.text
    assert rd_res.json()["is_read"] is True

    # Mark all as read
    mall_res = await client.post("/api/v1/notifications/read-all", headers=parent_headers)
    assert mall_res.status_code == 200, mall_res.text

    ucnt_res = await client.get("/api/v1/notifications/unread-count", headers=parent_headers)
    assert ucnt_res.status_code == 200, ucnt_res.text
    assert ucnt_res.json()["unread_count"] == 0


# ================================================================== #
# Subscriptions
# ================================================================== #

@pytest.mark.asyncio
async def test_subscriptions_lifecycle(client: AsyncClient, family_setup, parent_headers):
    """Test: get free sub, upgrade to pro, cancel."""
    # Default is free
    sub_res = await client.get("/api/v1/subscriptions", headers=parent_headers)
    assert sub_res.status_code == 200, sub_res.text
    assert sub_res.json()["tier"] == "free"

    # Upgrade to PRO
    up_res = await client.post("/api/v1/subscriptions/upgrade", headers=parent_headers)
    assert up_res.status_code == 200, up_res.text
    assert up_res.json()["tier"] == "pro"
    assert up_res.json()["max_seats"] == 6

    # Cancel
    cn_res = await client.post("/api/v1/subscriptions/cancel", headers=parent_headers)
    assert cn_res.status_code == 200, cn_res.text
    assert cn_res.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_subscription_double_upgrade_blocked(client: AsyncClient, family_setup, parent_headers):
    """M-3: Upgrading twice should be blocked to prevent free expiration extension."""
    # First upgrade
    up1 = await client.post("/api/v1/subscriptions/upgrade", headers=parent_headers)
    assert up1.status_code == 200

    # Second upgrade should be rejected
    up2 = await client.post("/api/v1/subscriptions/upgrade", headers=parent_headers)
    assert up2.status_code == 400
