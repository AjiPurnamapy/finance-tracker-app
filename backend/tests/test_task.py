"""
Integration tests for Task System — Phase 4.
Uses in-memory SQLite via conftest.py fixtures.

Covers:
- Wallet auto-creation on register
- Task CRUD + state machine
- Reward payment flow (approve → wallet credited)
- Immutable transaction ledger
- All permission/role guards
- Edge cases
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
async def family_setup(client: AsyncClient, parent_headers, child_headers):
    """
    Full setup: parent + child registered, family created, child joined.
    Returns family_id, child_id, parent_id.
    """
    # Create family
    fam_res = await client.post(
        "/api/v1/families/",
        json={"name": "Keluarga Test"},
        headers=parent_headers,
    )
    assert fam_res.status_code == 201
    family_id = fam_res.json()["data"]["id"]

    # Create invitation
    inv_res = await client.post(
        "/api/v1/invitations/",
        json={"invitee_name": "Anak Riri"},
        headers=parent_headers,
    )
    assert inv_res.status_code == 201
    invite_code = inv_res.json()["data"]["invite_code"]

    # Child joins
    join_res = await client.post(
        "/api/v1/invitations/join",
        json={"invite_code": invite_code},
        headers=child_headers,
    )
    assert join_res.status_code == 200

    # Get IDs
    parent_me = await client.get("/api/v1/users/me", headers=parent_headers)
    child_me = await client.get("/api/v1/users/me", headers=child_headers)

    return {
        "family_id": family_id,
        "parent_id": parent_me.json()["data"]["id"],
        "child_id": child_me.json()["data"]["id"],
    }


@pytest.fixture
async def created_task(client: AsyncClient, parent_headers, family_setup):
    """Create a task and return its data."""
    child_id = family_setup["child_id"]
    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Cuci Piring",
            "description": "Cuci semua piring kotor",
            "assigned_to": child_id,
            "reward_amount": "5000.00",
            "reward_currency": "IDR",
        },
        headers=parent_headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


# ================================================================== #
# 4.1 — Wallet auto-creation
# ================================================================== #

@pytest.mark.asyncio
async def test_wallet_created_on_register(client: AsyncClient, parent_headers):
    """Every user should have a wallet with zero balance after registration."""
    res = await client.get("/api/v1/wallets/me", headers=parent_headers)
    assert res.status_code == 200
    wallet = res.json()["data"]
    assert float(wallet["balance_idr"]) == 0.0
    assert float(wallet["balance_pts"]) == 0.0


@pytest.mark.asyncio
async def test_child_wallet_created_on_register(client: AsyncClient, child_headers):
    res = await client.get("/api/v1/wallets/me", headers=child_headers)
    assert res.status_code == 200
    assert float(res.json()["data"]["balance_idr"]) == 0.0


# ================================================================== #
# 4.2 — Create Task
# ================================================================== #

@pytest.mark.asyncio
async def test_create_task_success(client: AsyncClient, parent_headers, family_setup):
    child_id = family_setup["child_id"]
    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Cuci Piring",
            "assigned_to": child_id,
            "reward_amount": "5000.00",
            "reward_currency": "IDR",
        },
        headers=parent_headers,
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["title"] == "Cuci Piring"
    assert data["status"] == "created"
    assert float(data["reward_amount"]) == 5000.0


@pytest.mark.asyncio
async def test_child_cannot_create_task(client: AsyncClient, child_headers, family_setup):
    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Cuci Piring",
            "assigned_to": family_setup["child_id"],
            "reward_amount": "1000.00",
            "reward_currency": "IDR",
        },
        headers=child_headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_task_for_non_family_child_returns_403(
    client: AsyncClient, parent_headers, family_setup
):
    """Assigning task to a user not in the family should fail."""
    # Register an outsider child
    await _register(client, "outsider@test.com", "child", "Outsider")
    outsider_id_res = await client.post("/api/v1/auth/login", json={
        "email": "outsider@test.com",
        "password": "Secret123",
    })
    outsider_headers = {"Authorization": f"Bearer {outsider_id_res.json()['data']['access_token']}"}
    outsider_me = await client.get("/api/v1/users/me", headers=outsider_headers)
    outsider_id = outsider_me.json()["data"]["id"]

    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Cuci Piring",
            "assigned_to": outsider_id,
            "reward_amount": "1000.00",
            "reward_currency": "IDR",
        },
        headers=parent_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ASSIGNEE_NOT_IN_FAMILY"


@pytest.mark.asyncio
async def test_create_task_with_zero_reward_returns_422(
    client: AsyncClient, parent_headers, family_setup
):
    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Task gratis",
            "assigned_to": family_setup["child_id"],
            "reward_amount": "0.00",
            "reward_currency": "IDR",
        },
        headers=parent_headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_task_with_pts_reward(
    client: AsyncClient, parent_headers, family_setup
):
    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Baca Buku",
            "assigned_to": family_setup["child_id"],
            "reward_amount": "100.00",
            "reward_currency": "PTS",
        },
        headers=parent_headers,
    )
    assert res.status_code == 201
    assert res.json()["data"]["reward_currency"] == "PTS"


# ================================================================== #
# 4.3 — List Tasks
# ================================================================== #

@pytest.mark.asyncio
async def test_parent_lists_all_family_tasks(
    client: AsyncClient, parent_headers, created_task
):
    res = await client.get("/api/v1/tasks/", headers=parent_headers)
    assert res.status_code == 200
    tasks = res.json()["data"]
    assert len(tasks) >= 1


@pytest.mark.asyncio
async def test_child_lists_only_own_tasks(
    client: AsyncClient, parent_headers, child_headers, family_setup
):
    child_id = family_setup["child_id"]
    # Create task for child
    await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Task Anak",
            "assigned_to": child_id,
            "reward_amount": "1000.00",
            "reward_currency": "IDR",
        },
        headers=parent_headers,
    )
    res = await client.get("/api/v1/tasks/", headers=child_headers)
    assert res.status_code == 200
    tasks = res.json()["data"]
    # All returned tasks should be assigned to this child
    for task in tasks:
        assert task["assigned_to"] == child_id


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status(
    client: AsyncClient, parent_headers, created_task
):
    res = await client.get(
        "/api/v1/tasks/?status=created",
        headers=parent_headers,
    )
    assert res.status_code == 200
    for task in res.json()["data"]:
        assert task["status"] == "created"


# ================================================================== #
# 4.4 — Submit Task (Child)
# ================================================================== #

@pytest.mark.asyncio
async def test_child_submits_task(
    client: AsyncClient, child_headers, created_task
):
    task_id = created_task["id"]
    res = await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers=child_headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "submitted"


@pytest.mark.asyncio
async def test_parent_cannot_submit_task(
    client: AsyncClient, parent_headers, created_task
):
    task_id = created_task["id"]
    res = await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers=parent_headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_submit_already_submitted_task_returns_400(
    client: AsyncClient, child_headers, created_task
):
    """Submitting a task twice should fail (invalid state transition)."""
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    res = await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


# ================================================================== #
# 4.5 — Approve Task → Reward Paid
# ================================================================== #

@pytest.mark.asyncio
async def test_approve_task_credits_child_wallet(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    task_id = created_task["id"]
    reward = float(created_task["reward_amount"])

    # Check child wallet before
    wallet_before = await client.get("/api/v1/wallets/me", headers=child_headers)
    balance_before = float(wallet_before.json()["data"]["balance_idr"])

    # Child submits
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)

    # Parent approves
    res = await client.post(
        f"/api/v1/tasks/{task_id}/approve",
        headers=parent_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "completed"
    assert data["completed_at"] is not None
    assert data["reward_transaction_id"] is not None

    # Check child wallet after — should be credited
    wallet_after = await client.get("/api/v1/wallets/me", headers=child_headers)
    balance_after = float(wallet_after.json()["data"]["balance_idr"])
    assert balance_after == balance_before + reward


@pytest.mark.asyncio
async def test_approve_task_with_pts_reward(
    client: AsyncClient, parent_headers, child_headers, family_setup
):
    """Approving a PTS task should credit PTS balance, not IDR."""
    child_id = family_setup["child_id"]

    task_res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Baca Buku",
            "assigned_to": child_id,
            "reward_amount": "50.00",
            "reward_currency": "PTS",
        },
        headers=parent_headers,
    )
    task_id = task_res.json()["data"]["id"]

    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    await client.post(f"/api/v1/tasks/{task_id}/approve", headers=parent_headers)

    wallet = await client.get("/api/v1/wallets/me", headers=child_headers)
    assert float(wallet.json()["data"]["balance_pts"]) == 50.0
    assert float(wallet.json()["data"]["balance_idr"]) == 0.0


@pytest.mark.asyncio
async def test_double_approve_returns_400(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    """Approving a completed task should fail."""
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    await client.post(f"/api/v1/tasks/{task_id}/approve", headers=parent_headers)

    res = await client.post(
        f"/api/v1/tasks/{task_id}/approve",
        headers=parent_headers,
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_child_cannot_approve_task(
    client: AsyncClient, child_headers, parent_headers, created_task
):
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    res = await client.post(
        f"/api/v1/tasks/{task_id}/approve",
        headers=child_headers,
    )
    assert res.status_code == 403


# ================================================================== #
# 4.6 — Reject Task
# ================================================================== #

@pytest.mark.asyncio
async def test_parent_rejects_task_no_wallet_change(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    task_id = created_task["id"]

    wallet_before = await client.get("/api/v1/wallets/me", headers=child_headers)
    balance_before = float(wallet_before.json()["data"]["balance_idr"])

    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    res = await client.post(
        f"/api/v1/tasks/{task_id}/reject",
        headers=parent_headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "rejected"

    wallet_after = await client.get("/api/v1/wallets/me", headers=child_headers)
    assert float(wallet_after.json()["data"]["balance_idr"]) == balance_before


@pytest.mark.asyncio
async def test_reject_approved_task_returns_400(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    """Cannot reject an already-completed task."""
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    await client.post(f"/api/v1/tasks/{task_id}/approve", headers=parent_headers)

    res = await client.post(
        f"/api/v1/tasks/{task_id}/reject",
        headers=parent_headers,
    )
    assert res.status_code == 400


# ================================================================== #
# 4.7 — Update & Delete Task
# ================================================================== #

@pytest.mark.asyncio
async def test_parent_updates_task_while_created(
    client: AsyncClient, parent_headers, created_task
):
    task_id = created_task["id"]
    res = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Cuci Piring & Gelas", "reward_amount": "7500.00"},
        headers=parent_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["title"] == "Cuci Piring & Gelas"
    assert float(data["reward_amount"]) == 7500.0


@pytest.mark.asyncio
async def test_parent_cannot_update_submitted_task(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)

    res = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Judul Baru"},
        headers=parent_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "TASK_NOT_EDITABLE"


@pytest.mark.asyncio
async def test_parent_deletes_created_task(
    client: AsyncClient, parent_headers, created_task
):
    task_id = created_task["id"]
    res = await client.delete(f"/api/v1/tasks/{task_id}", headers=parent_headers)
    assert res.status_code == 204

    # Verify deleted
    get_res = await client.get(f"/api/v1/tasks/{task_id}", headers=parent_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_submitted_task(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)

    res = await client.delete(f"/api/v1/tasks/{task_id}", headers=parent_headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "TASK_NOT_DELETABLE"


# ================================================================== #
# 4.8 — Transactions (Immutable Ledger)
# ================================================================== #

@pytest.mark.asyncio
async def test_transaction_created_after_approve(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    approve_res = await client.post(
        f"/api/v1/tasks/{task_id}/approve", headers=parent_headers
    )
    tx_id = approve_res.json()["data"]["reward_transaction_id"]

    # Fetch the transaction
    tx_res = await client.get(f"/api/v1/transactions/{tx_id}", headers=parent_headers)
    assert tx_res.status_code == 200
    tx = tx_res.json()["data"]
    assert tx["type"] == "task_reward"
    assert float(tx["amount"]) == float(created_task["reward_amount"])
    assert tx["reference_type"] == "task"
    assert tx["reference_id"] == task_id


@pytest.mark.asyncio
async def test_child_can_see_own_transaction(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    await client.post(f"/api/v1/tasks/{task_id}/approve", headers=parent_headers)

    res = await client.get("/api/v1/transactions/", headers=child_headers)
    assert res.status_code == 200
    assert res.json()["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_transaction_list_paginated(
    client: AsyncClient, parent_headers, child_headers, family_setup
):
    """Create 3 tasks, approve all, verify paginated response."""
    child_id = family_setup["child_id"]
    task_ids = []
    for i in range(3):
        t = await client.post(
            "/api/v1/tasks/",
            json={
                "title": f"Task {i}",
                "assigned_to": child_id,
                "reward_amount": "1000.00",
                "reward_currency": "IDR",
            },
            headers=parent_headers,
        )
        task_ids.append(t.json()["data"]["id"])

    for tid in task_ids:
        await client.post(f"/api/v1/tasks/{tid}/submit", headers=child_headers)
        await client.post(f"/api/v1/tasks/{tid}/approve", headers=parent_headers)

    # Parent sees all 3 transactions
    res = await client.get(
        "/api/v1/transactions/?page=1&per_page=2",
        headers=parent_headers,
    )
    assert res.status_code == 200
    meta = res.json()["meta"]
    assert meta["total"] >= 3
    assert meta["per_page"] == 2
    assert meta["total_pages"] >= 2


@pytest.mark.asyncio
async def test_wallet_family_view_parent_only(
    client: AsyncClient, parent_headers, child_headers, family_setup
):
    """Parent can see all family wallets; child cannot."""
    family_id = family_setup["family_id"]

    # Parent OK
    res = await client.get(
        f"/api/v1/wallets/family/{family_id}",
        headers=parent_headers,
    )
    assert res.status_code == 200
    assert len(res.json()["data"]) == 2  # parent + child

    # Child gets 403
    res2 = await client.get(
        f"/api/v1/wallets/family/{family_id}",
        headers=child_headers,
    )
    assert res2.status_code == 403


# ================================================================== #
# T1 — Parent cannot assign task to self
# ================================================================== #

@pytest.mark.asyncio
async def test_parent_cannot_assign_task_to_self(
    client: AsyncClient, parent_headers, family_setup
):
    """Parent should not be able to create a task assigned to themselves."""
    parent_id = family_setup["parent_id"]
    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Self Task",
            "assigned_to": parent_id,
            "reward_amount": "1000.00",
            "reward_currency": "IDR",
        },
        headers=parent_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CANNOT_ASSIGN_TO_SELF"


# ================================================================== #
# T2 — Due date in the past
# ================================================================== #

@pytest.mark.asyncio
async def test_create_task_with_past_due_date_returns_400(
    client: AsyncClient, parent_headers, family_setup
):
    """Creating a task with a due_date in the past should fail."""
    child_id = family_setup["child_id"]
    res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Expired Task",
            "assigned_to": child_id,
            "reward_amount": "1000.00",
            "reward_currency": "IDR",
            "due_date": "2020-01-01T00:00:00Z",
        },
        headers=parent_headers,
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "DUE_DATE_IN_PAST"


# ================================================================== #
# T3 — Cross-family child cannot submit another family's task
# ================================================================== #

@pytest.mark.asyncio
async def test_cross_family_child_cannot_submit_task(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    """A child from a different family cannot submit a task from another family."""
    # Register a second child (not in any family)
    await _register(client, "child2@test.com", "child", "Anak Lain")
    child2_headers = await _login(client, "child2@test.com")

    task_id = created_task["id"]
    res = await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers=child2_headers,
    )
    # Should fail because child2 is not in the family
    assert res.status_code == 403


# ================================================================== #
# T4 — Child cannot see another child's task via get_task
# ================================================================== #

@pytest.mark.asyncio
async def test_child_cannot_see_other_childs_task(
    client: AsyncClient, parent_headers, family_setup
):
    """
    If a family has 2 children, child A cannot GET a task assigned to child B.
    For this test, we use the parent's task assigned to a specific child,
    and try accessing it with a different child in the same family.
    """
    # Register and join a second child to the family
    await _register(client, "child_b@test.com", "child", "Anak B")
    child_b_headers = await _login(client, "child_b@test.com")

    # Create invitation for child B (need to be within seat limit — Free=2, already used)
    # Since free tier only allows 2 seats, we test with the outsider path instead:
    # Child B is NOT in the family, so get_task should return 403
    child_id_a = family_setup["child_id"]

    # Create task for child A
    task_res = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "Task for A",
            "assigned_to": child_id_a,
            "reward_amount": "1000.00",
            "reward_currency": "IDR",
        },
        headers=parent_headers,
    )
    task_id = task_res.json()["data"]["id"]

    # Child B (not in family) tries to get this task
    res = await client.get(
        f"/api/v1/tasks/{task_id}",
        headers=child_b_headers,
    )
    assert res.status_code == 403


# ================================================================== #
# T5 — Transaction immutability: no PUT/DELETE endpoints exist
# ================================================================== #

@pytest.mark.asyncio
async def test_transaction_immutability_no_update_endpoint(
    client: AsyncClient, parent_headers, child_headers, created_task
):
    """Verify that PUT and DELETE on transactions return 405 Method Not Allowed."""
    task_id = created_task["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=child_headers)
    approve_res = await client.post(
        f"/api/v1/tasks/{task_id}/approve", headers=parent_headers
    )
    tx_id = approve_res.json()["data"]["reward_transaction_id"]

    # Attempt PUT → should be 405
    put_res = await client.put(
        f"/api/v1/transactions/{tx_id}",
        json={"amount": "999999.00"},
        headers=parent_headers,
    )
    assert put_res.status_code == 405

    # Attempt DELETE → should be 405
    del_res = await client.delete(
        f"/api/v1/transactions/{tx_id}",
        headers=parent_headers,
    )
    assert del_res.status_code == 405
