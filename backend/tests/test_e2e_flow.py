"""
End-to-End Integration Test Suite — Phase 7

Simulates complete user journeys from registration through full business workflows.
Each test is independent with its own DB + users to avoid cross-test contamination.

Flows:
  1. Happy Path          — full task lifecycle with notification verification
  2. Fund Request        — child request → parent approve → wallet verification
  3. Savings Goal        — contribute with milestone notification verification
  4. PTS System          — PTS reward task → exchange to IDR
  5. Permission Boundary — verify all role-based access controls
"""

import pytest
from decimal import Decimal
from httpx import AsyncClient


# ================================================================== #
# Helper utilities
# ================================================================== #

async def register(client: AsyncClient, email: str, role: str, name: str) -> dict:
    res = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Secret123",
        "full_name": name,
        "role": role,
    })
    assert res.status_code == 201, f"Register failed: {res.text}"
    return res.json()["data"]


async def login(client: AsyncClient, email: str) -> dict:
    res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Secret123",
    })
    assert res.status_code == 200, f"Login failed: {res.text}"
    return {"Authorization": f"Bearer {res.json()['data']['access_token']}"}


async def setup_family(client: AsyncClient, parent_h: dict, child_h: dict) -> str:
    """Create a family, invite child, child joins. Returns family_id."""
    family_res = await client.post("/api/v1/families/", json={"name": "E2E Family"}, headers=parent_h)
    assert family_res.status_code == 201, family_res.text
    family_id = family_res.json()["data"]["id"]

    inv_res = await client.post("/api/v1/invitations/", json={"invitee_name": "Anak E2E"}, headers=parent_h)
    assert inv_res.status_code == 201, inv_res.text
    code = inv_res.json()["data"]["invite_code"]

    join_res = await client.post("/api/v1/invitations/join", json={"invite_code": code}, headers=child_h)
    assert join_res.status_code == 200, join_res.text
    return family_id


async def topup(client: AsyncClient, headers: dict, amount: str = "500000.00") -> None:
    res = await client.post("/api/v1/wallets/topup", json={"amount": amount, "description": "E2E topup"}, headers=headers)
    assert res.status_code == 200, res.text


async def get_wallet(client: AsyncClient, headers: dict) -> dict:
    res = await client.get("/api/v1/wallets/me", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()["data"]


# ================================================================== #
# Flow 1: Happy Path — Full Task Lifecycle
# ================================================================== #

@pytest.mark.asyncio
async def test_e2e_flow1_happy_path(client: AsyncClient):
    """
    Full happy path:
    Register parent & child → family setup → parent creates task
    → child submits → parent approves → verify wallet + transaction + notification
    """
    # Setup users
    parent_h = await login(client, (await register(client, "e2e_p1@test.com", "parent", "Parent E2E"))["email"])
    child_h = await login(client, (await register(client, "e2e_c1@test.com", "child", "Child E2E"))["email"])

    child_me = await client.get("/api/v1/users/me", headers=child_h)
    child_id = child_me.json()["data"]["id"]

    await setup_family(client, parent_h, child_h)

    # Check initial wallet balance
    initial_wallet = await get_wallet(client, child_h)
    initial_idr = Decimal(str(initial_wallet["balance_idr"]))

    # Parent creates task with IDR reward
    task_res = await client.post("/api/v1/tasks/", json={
        "assigned_to": child_id,
        "title": "Cuci Piring E2E",
        "reward_amount": 5000.00,
        "reward_currency": "IDR",
        "is_recurring": False,
    }, headers=parent_h)
    assert task_res.status_code == 201, task_res.text
    task_id = task_res.json()["data"]["id"]

    # Child submits task
    sub_res = await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_h)
    assert sub_res.status_code == 200, sub_res.text
    assert sub_res.json()["data"]["status"] == "submitted"

    # Parent should have a notification (task submitted)
    notif_res = await client.get("/api/v1/notifications?page=1&per_page=20", headers=parent_h)
    assert notif_res.status_code == 200
    notifications = notif_res.json()
    assert len(notifications) > 0
    notif_types = [n["type"] for n in notifications]
    assert "task_submitted" in notif_types

    # Parent approves task
    approve_res = await client.post(f"/api/v1/tasks/{task_id}/approve", headers=parent_h)
    assert approve_res.status_code == 200, approve_res.text
    assert approve_res.json()["data"]["status"] == "completed"

    # Verify child wallet increased by reward amount
    final_wallet = await get_wallet(client, child_h)
    final_idr = Decimal(str(final_wallet["balance_idr"]))
    assert final_idr == initial_idr + Decimal("5000.00"), \
        f"Expected {initial_idr + 5000}, got {final_idr}"

    # Child should have a notification (task approved)
    child_notif_res = await client.get("/api/v1/notifications?page=1&per_page=20", headers=child_h)
    assert child_notif_res.status_code == 200
    child_notifications = child_notif_res.json()
    assert any(n["type"] == "task_approved" for n in child_notifications)

    # Verify transaction record exists
    txn_res = await client.get("/api/v1/transactions/?page=1&per_page=10", headers=child_h)
    assert txn_res.status_code == 200
    txns = txn_res.json()["data"]
    assert any(t["type"] == "task_reward" for t in txns)

    # Mark notification as read
    notif_id = notifications[0]["id"]
    read_res = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=parent_h)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Unread count should decrease
    unread_res = await client.get("/api/v1/notifications/unread-count", headers=parent_h)
    assert unread_res.status_code == 200
    assert unread_res.json()["unread_count"] < len(notifications)


# ================================================================== #
# Flow 2: Fund Request Lifecycle
# ================================================================== #

@pytest.mark.asyncio
async def test_e2e_flow2_fund_request(client: AsyncClient):
    """
    Fund request flow:
    Child requests Rp 20.000 → parent approves
    → child wallet +20.000, parent wallet -20.000
    """
    parent_h = await login(client, (await register(client, "e2e_p2@test.com", "parent", "Parent FR"))["email"])
    child_h = await login(client, (await register(client, "e2e_c2@test.com", "child", "Child FR"))["email"])

    await setup_family(client, parent_h, child_h)

    # Parent tops up wallet first
    await topup(client, parent_h, "100000.00")
    parent_wallet_before = await get_wallet(client, parent_h)
    parent_idr_before = Decimal(str(parent_wallet_before["balance_idr"]))

    child_wallet_before = await get_wallet(client, child_h)
    child_idr_before = Decimal(str(child_wallet_before["balance_idr"]))

    # Child creates fund request
    req_res = await client.post("/api/v1/fund-requests/", json={
        "amount": 20000.00,
        "currency": "IDR",
        "type": "one_time",
        "reason": "Beli buku pelajaran",
    }, headers=child_h)
    assert req_res.status_code == 201, req_res.text
    request_id = req_res.json()["data"]["id"]
    assert req_res.json()["data"]["status"] == "pending"

    # Parent approves
    approve_res = await client.post(f"/api/v1/fund-requests/{request_id}/approve", headers=parent_h)
    assert approve_res.status_code == 200, approve_res.text
    assert approve_res.json()["data"]["status"] == "approved"

    # Verify wallet changes
    parent_wallet_after = await get_wallet(client, parent_h)
    child_wallet_after = await get_wallet(client, child_h)

    parent_idr_after = Decimal(str(parent_wallet_after["balance_idr"]))
    child_idr_after = Decimal(str(child_wallet_after["balance_idr"]))

    assert parent_idr_after == parent_idr_before - Decimal("20000.00"), \
        f"Parent wallet expected {parent_idr_before - 20000}, got {parent_idr_after}"
    assert child_idr_after == child_idr_before + Decimal("20000.00"), \
        f"Child wallet expected {child_idr_before + 20000}, got {child_idr_after}"

    # Child should have approval notification
    child_notifs = await client.get("/api/v1/notifications?page=1&per_page=20", headers=child_h)
    assert any(n["type"] == "fund_request_approved" for n in child_notifs.json())


# ================================================================== #
# Flow 3: Savings Goal with Milestone Notifications
# ================================================================== #

@pytest.mark.asyncio
async def test_e2e_flow3_savings_goal(client: AsyncClient):
    """
    Savings goal flow:
    Child creates goal Rp 100.000 → contributes 25% → verify milestone notif
    → contributes to 100% → verify completed
    """
    parent_h = await login(client, (await register(client, "e2e_p3@test.com", "parent", "Parent SG"))["email"])
    child_h = await login(client, (await register(client, "e2e_c3@test.com", "child", "Child SG"))["email"])

    child_me = await client.get("/api/v1/users/me", headers=child_h)
    child_id = child_me.json()["data"]["id"]
    await setup_family(client, parent_h, child_h)

    # Fund child wallet via allowance
    alw_res = await client.post("/api/v1/allowances/", json={
        "child_id": child_id,
        "amount": 200000.00,
        "currency": "IDR",
        "is_recurring": False,
    }, headers=parent_h)
    assert alw_res.status_code == 201
    allowance_id = alw_res.json()["data"]["id"]
    await topup(client, parent_h, "300000.00")
    trf_res = await client.post(f"/api/v1/allowances/{allowance_id}/transfer", headers=parent_h)
    assert trf_res.status_code == 200

    # Child creates savings goal
    goal_res = await client.post("/api/v1/savings-goals", json={
        "name": "Nintendo Switch",
        "target_amount": 100000.00,
    }, headers=child_h)
    assert goal_res.status_code == 201, goal_res.text
    goal_id = goal_res.json()["id"]
    assert goal_res.json()["is_completed"] is False
    assert float(goal_res.json()["current_amount"]) == 0.0

    # Contribute 25% → should trigger 25% milestone notification
    ct1_res = await client.post(f"/api/v1/savings-goals/{goal_id}/contribute",
                                json={"amount": 25000.00}, headers=child_h)
    assert ct1_res.status_code == 200, ct1_res.text
    assert float(ct1_res.json()["current_amount"]) == 25000.0
    assert ct1_res.json()["is_completed"] is False

    # Verify milestone notification sent
    notifs = (await client.get("/api/v1/notifications?page=1&per_page=20", headers=child_h)).json()
    assert any(n["type"] == "goal_milestone" and n["data"]["milestone"] == 25 for n in notifs)

    # Contribute 50% → should trigger 50% milestone
    ct2_res = await client.post(f"/api/v1/savings-goals/{goal_id}/contribute",
                                json={"amount": 25000.00}, headers=child_h)
    assert ct2_res.status_code == 200
    notifs2 = (await client.get("/api/v1/notifications?page=1&per_page=20", headers=child_h)).json()
    assert any(n["type"] == "goal_milestone" and n["data"]["milestone"] == 50 for n in notifs2)

    # Contribute remaining 50% to complete
    ct3_res = await client.post(f"/api/v1/savings-goals/{goal_id}/contribute",
                                json={"amount": 50000.00}, headers=child_h)
    assert ct3_res.status_code == 200, ct3_res.text
    assert ct3_res.json()["is_completed"] is True
    assert float(ct3_res.json()["current_amount"]) == 100000.0

    # Verify 100% milestone notification
    notifs3 = (await client.get("/api/v1/notifications?page=1&per_page=20", headers=child_h)).json()
    assert any(n["type"] == "goal_milestone" and n["data"]["milestone"] == 100 for n in notifs3)

    # Verify cannot contribute to completed goal
    ct4_res = await client.post(f"/api/v1/savings-goals/{goal_id}/contribute",
                                json={"amount": 1000.00}, headers=child_h)
    assert ct4_res.status_code == 400
    assert ct4_res.json()["error"]["code"] == "GOAL_COMPLETED"


# ================================================================== #
# Flow 4: PTS System
# ================================================================== #

@pytest.mark.asyncio
async def test_e2e_flow4_pts_system(client: AsyncClient, pts_exchange_rate):
    """
    PTS reward flow:
    Parent creates PTS task → child submits → parent approves
    → child has PTS balance → exchange PTS to IDR → verify conversion
    """
    parent_h = await login(client, (await register(client, "e2e_p4@test.com", "parent", "Parent PTS"))["email"])
    child_h = await login(client, (await register(client, "e2e_c4@test.com", "child", "Child PTS"))["email"])

    child_me = await client.get("/api/v1/users/me", headers=child_h)
    child_id = child_me.json()["data"]["id"]
    await setup_family(client, parent_h, child_h)

    # Parent creates task with PTS reward
    task_res = await client.post("/api/v1/tasks/", json={
        "assigned_to": child_id,
        "title": "Belajar Matematika",
        "reward_amount": 1000,
        "reward_currency": "PTS",
        "is_recurring": False,
    }, headers=parent_h)
    assert task_res.status_code == 201, task_res.text
    task_id = task_res.json()["data"]["id"]

    # Verify initial PTS balance
    wallet_before = await get_wallet(client, child_h)
    pts_before = Decimal(str(wallet_before["balance_pts"]))

    # Child submits, parent approves
    submit_res = await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_h)
    assert submit_res.status_code == 200

    approve_res = await client.post(f"/api/v1/tasks/{task_id}/approve", headers=parent_h)
    assert approve_res.status_code == 200

    # Verify PTS credited
    wallet_after = await get_wallet(client, child_h)
    pts_after = Decimal(str(wallet_after["balance_pts"]))
    assert pts_after == pts_before + Decimal("1000"), \
        f"Expected {pts_before + 1000} PTS, got {pts_after}"

    # Exchange 1000 PTS → IDR (rate: 1000 PTS = Rp 10.000 from pts_exchange_rate fixture)
    idr_before = Decimal(str(wallet_after["balance_idr"]))

    exchange_res = await client.post("/api/v1/wallets/exchange-pts", json={
        "pts_amount": 1000,
    }, headers=child_h)
    assert exchange_res.status_code == 200, exchange_res.text

    exchange_data = exchange_res.json()["data"]
    assert Decimal(str(exchange_data["pts_deducted"])) == Decimal("1000")
    assert Decimal(str(exchange_data["idr_credited"])) == Decimal("10000")

    # Verify wallet: PTS = 0, IDR increased by 10.000
    wallet_final = await get_wallet(client, child_h)
    assert Decimal(str(wallet_final["balance_pts"])) == Decimal("0")
    assert Decimal(str(wallet_final["balance_idr"])) == idr_before + Decimal("10000")


# ================================================================== #
# Flow 5: Permission Boundaries
# ================================================================== #

@pytest.mark.asyncio
async def test_e2e_flow5_permission_boundaries(client: AsyncClient):
    """
    Verify all role-based access controls are enforced:
    - Child cannot create task
    - Child cannot approve task
    - Parent cannot submit task
    - User from another family cannot access first family's tasks
    - Unauthenticated request → 401
    """
    # Setup family A
    parent_a = await login(client, (await register(client, "e2e_pa@test.com", "parent", "Parent A"))["email"])
    child_a = await login(client, (await register(client, "e2e_ca@test.com", "child", "Child A"))["email"])
    child_a_id_res = await client.get("/api/v1/users/me", headers=child_a)
    child_a_id = child_a_id_res.json()["data"]["id"]
    await setup_family(client, parent_a, child_a)

    # Setup family B (different family)
    parent_b = await login(client, (await register(client, "e2e_pb@test.com", "parent", "Parent B"))["email"])
    child_b = await login(client, (await register(client, "e2e_cb@test.com", "child", "Child B"))["email"])
    child_b_id_res = await client.get("/api/v1/users/me", headers=child_b)
    child_b_id = child_b_id_res.json()["data"]["id"]
    await setup_family(client, parent_b, child_b)

    # Create task in family A
    task_res = await client.post("/api/v1/tasks/", json={
        "assigned_to": child_a_id,
        "title": "Task Family A",
        "reward_amount": 1000,
        "reward_currency": "IDR",
        "is_recurring": False,
    }, headers=parent_a)
    assert task_res.status_code == 201
    task_a_id = task_res.json()["data"]["id"]

    # 1. Child cannot CREATE task
    child_create = await client.post("/api/v1/tasks/", json={
        "assigned_to": child_a_id,
        "title": "Unauthorized",
        "reward_amount": 1000,
        "reward_currency": "IDR",
        "is_recurring": False,
    }, headers=child_a)
    assert child_create.status_code == 403, f"Expected 403, got {child_create.status_code}"

    # 2. Child cannot APPROVE task
    child_approve = await client.post(f"/api/v1/tasks/{task_a_id}/approve", headers=child_a)
    assert child_approve.status_code == 403, f"Expected 403, got {child_approve.status_code}"

    # 3. Parent cannot SUBMIT task
    parent_submit = await client.post(f"/api/v1/tasks/{task_a_id}/submit", headers=parent_a)
    assert parent_submit.status_code == 403, f"Expected 403, got {parent_submit.status_code}"

    # 4. Parent cannot create savings goal (child-only)
    parent_goal = await client.post("/api/v1/savings-goals", json={
        "name": "Unauthorized Goal",
        "target_amount": 10000,
    }, headers=parent_a)
    assert parent_goal.status_code == 403, f"Expected 403, got {parent_goal.status_code}"

    # 5. Child from family B cannot access family A's task
    # First child B submits their own assigned task (but can't submit task_a)
    cross_submit = await client.post(f"/api/v1/tasks/{task_a_id}/submit", headers=child_b)
    assert cross_submit.status_code in (403, 404), \
        f"Cross-family access should be 403/404, got {cross_submit.status_code}"

    # 6. Unauthenticated request → 401
    no_auth = await client.get("/api/v1/users/me")
    assert no_auth.status_code == 401, f"Expected 401, got {no_auth.status_code}"

    # 7. Child cannot upgrade subscription (parent only)
    child_upgrade = await client.post("/api/v1/subscriptions/upgrade", headers=child_a)
    assert child_upgrade.status_code == 403
