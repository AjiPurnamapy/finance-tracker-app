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

@pytest.mark.asyncio
async def test_savings_goals(client: AsyncClient, family_setup, parent_headers, child_headers):
    # 1. Get child ID
    me_resp = await client.get("/api/v1/users/me", headers=child_headers)
    child_id = me_resp.json()["data"]["id"]

    # 2. Parent create allowance
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

    # 2.5 Parent topup wallet
    topup_res = await client.post(
        "/api/v1/wallets/topup",
        json={"amount": "500000.00", "description": "test topup"},
        headers=parent_headers,
    )
    assert topup_res.status_code == 200, topup_res.text

    # 3. Parent manual transfer
    trf_res = await client.post(
        f"/api/v1/allowances/{allowance_id}/transfer",
        headers=parent_headers,
    )
    assert trf_res.status_code == 200, trf_res.text

    # 4. Child creates savings goal
    sg_res = await client.post(
        "/api/v1/savings-goals",
        json={"name": "Beli Mainan", "target_amount": 50000.00},
        headers=child_headers,
    )
    assert sg_res.status_code == 201, sg_res.text
    goal_id = sg_res.json()["id"]

    # 5. Child contributes
    ct_res = await client.post(
        f"/api/v1/savings-goals/{goal_id}/contribute",
        json={"amount": 25000.00},
        headers=child_headers,
    )
    assert ct_res.status_code == 200, ct_res.text
    assert float(ct_res.json()["current_amount"]) == 25000.0

    # 6. Child contributes again to reach target
    ct2_res = await client.post(
        f"/api/v1/savings-goals/{goal_id}/contribute",
        json={"amount": 25000.00},
        headers=child_headers,
    )
    assert ct2_res.status_code == 200, ct2_res.text
    assert ct2_res.json()["is_completed"] is True
    assert float(ct2_res.json()["current_amount"]) == 50000.0

@pytest.mark.asyncio
async def test_notifications(client: AsyncClient, family_setup, parent_headers, child_headers):
    me_resp = await client.get("/api/v1/users/me", headers=child_headers)
    child_id = me_resp.json()["data"]["id"]

    # 1. Create task
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

    # 2. Child submit task
    sub_res = await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers=child_headers,
    )
    assert sub_res.status_code == 200, sub_res.text

    # 3. Parent check notifications
    ntf_res = await client.get("/api/v1/notifications", headers=parent_headers)
    assert ntf_res.status_code == 200, ntf_res.text
    notifications = ntf_res.json()
    assert len(notifications) > 0

    # 4. Read first notification
    notif_id = notifications[0]["id"]
    rd_res = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=parent_headers)
    assert rd_res.status_code == 200, rd_res.text
    assert rd_res.json()["is_read"] is True

    # 5. Mark all as read
    mall_res = await client.post("/api/v1/notifications/read-all", headers=parent_headers)
    assert mall_res.status_code == 200, mall_res.text
    
    ucnt_res = await client.get("/api/v1/notifications/unread-count", headers=parent_headers)
    assert ucnt_res.status_code == 200, ucnt_res.text
    assert ucnt_res.json()["unread_count"] == 0

@pytest.mark.asyncio
async def test_subscriptions(client: AsyncClient, family_setup, parent_headers):
    # 1. Get subscription
    sub_res = await client.get("/api/v1/subscriptions", headers=parent_headers)
    assert sub_res.status_code == 200, sub_res.text
    assert sub_res.json()["tier"] == "free"

    # 2. Upgrade
    up_res = await client.post("/api/v1/subscriptions/upgrade", headers=parent_headers)
    assert up_res.status_code == 200, up_res.text
    assert up_res.json()["tier"] == "pro"
    assert up_res.json()["max_seats"] == 6

    # 3. Cancel
    cn_res = await client.post("/api/v1/subscriptions/cancel", headers=parent_headers)
    assert cn_res.status_code == 200, cn_res.text
    assert cn_res.json()["status"] == "canceled"
