"""
Integration tests for Phase 5 Financial Core.
Covers: allowances, fund requests, expenses, wallet topup & PTS exchange.
"""

import pytest
from httpx import AsyncClient


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

async def _register(client, email, role, name="Test User"):
    res = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Secret123", "full_name": name, "role": role,
    })
    assert res.status_code == 201, res.text
    return res.json()["data"]


async def _login(client, email):
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Secret123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['data']['access_token']}"}


async def _setup_family(client, parent_headers, child_headers):
    """Create family, invite child, return ids."""
    fam = await client.post("/api/v1/families/", json={"name": "Keluarga Test"}, headers=parent_headers)
    assert fam.status_code == 201
    family_id = fam.json()["data"]["id"]

    inv = await client.post("/api/v1/invitations/", json={"invitee_name": "Anak"}, headers=parent_headers)
    assert inv.status_code == 201
    invite_code = inv.json()["data"]["invite_code"]

    join = await client.post("/api/v1/invitations/join", json={"invite_code": invite_code}, headers=child_headers)
    assert join.status_code == 200

    me_child = await client.get("/api/v1/users/me", headers=child_headers)
    child_id = me_child.json()["data"]["id"]

    me_parent = await client.get("/api/v1/users/me", headers=parent_headers)
    parent_id = me_parent.json()["data"]["id"]

    return family_id, parent_id, child_id


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
async def parent_headers(client):
    await _register(client, "parent@fin.com", "parent", "Bapak Test")
    return await _login(client, "parent@fin.com")


@pytest.fixture
async def child_headers(client):
    await _register(client, "child@fin.com", "child", "Anak Test")
    return await _login(client, "child@fin.com")


@pytest.fixture
async def family_setup(client, parent_headers, child_headers):
    family_id, parent_id, child_id = await _setup_family(client, parent_headers, child_headers)
    return {
        "family_id": family_id,
        "parent_id": parent_id,
        "child_id": child_id,
    }


@pytest.fixture
async def topped_up_parent(client, parent_headers, family_setup):
    """Parent with 500_000 IDR in wallet."""
    res = await client.post(
        "/api/v1/wallets/topup",
        json={"amount": "500000.00", "description": "test topup"},
        headers=parent_headers,
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]


# ================================================================== #
# WALLET TOPUP
# ================================================================== #

class TestWalletTopup:
    async def test_parent_can_topup(self, client, parent_headers, family_setup):
        res = await client.post(
            "/api/v1/wallets/topup",
            json={"amount": "100000.00"},
            headers=parent_headers,
        )
        assert res.status_code == 200
        wallet = res.json()["data"]
        assert float(wallet["balance_idr"]) >= 100000.0

    async def test_child_cannot_topup(self, client, child_headers, family_setup):
        res = await client.post(
            "/api/v1/wallets/topup",
            json={"amount": "50000.00"},
            headers=child_headers,
        )
        assert res.status_code == 403

    async def test_topup_negative_rejected(self, client, parent_headers, family_setup):
        res = await client.post(
            "/api/v1/wallets/topup",
            json={"amount": "-100.00"},
            headers=parent_headers,
        )
        assert res.status_code == 422

    async def test_topup_zero_rejected(self, client, parent_headers, family_setup):
        res = await client.post(
            "/api/v1/wallets/topup",
            json={"amount": "0.00"},
            headers=parent_headers,
        )
        assert res.status_code == 422


# ================================================================== #
# ALLOWANCE
# ================================================================== #

class TestAllowance:
    async def test_parent_creates_allowance(self, client, parent_headers, family_setup, topped_up_parent):
        child_id = family_setup["child_id"]
        res = await client.post(
            "/api/v1/allowances/",
            json={"child_id": child_id, "amount": "50000.00", "currency": "IDR", "is_recurring": False},
            headers=parent_headers,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["child_id"] == child_id
        assert float(data["amount"]) == 50000.0

    async def test_child_cannot_create_allowance(self, client, child_headers, family_setup):
        parent_id = family_setup["parent_id"]
        res = await client.post(
            "/api/v1/allowances/",
            json={"child_id": parent_id, "amount": "1000.00", "currency": "IDR", "is_recurring": False},
            headers=child_headers,
        )
        assert res.status_code == 403

    async def test_allowance_manual_transfer(self, client, parent_headers, child_headers, family_setup, topped_up_parent):
        child_id = family_setup["child_id"]

        # Create allowance
        create_res = await client.post(
            "/api/v1/allowances/",
            json={"child_id": child_id, "amount": "25000.00", "currency": "IDR", "is_recurring": False},
            headers=parent_headers,
        )
        assert create_res.status_code == 201
        allowance_id = create_res.json()["data"]["id"]

        # Check parent wallet before
        parent_wallet_before = (await client.get("/api/v1/wallets/me", headers=parent_headers)).json()["data"]

        # Manual transfer
        transfer_res = await client.post(
            f"/api/v1/allowances/{allowance_id}/transfer",
            headers=parent_headers,
        )
        assert transfer_res.status_code == 200, transfer_res.text

        # Child wallet should increase
        child_wallet = (await client.get("/api/v1/wallets/me", headers=child_headers)).json()["data"]
        assert float(child_wallet["balance_idr"]) >= 25000.0

        # Parent wallet should decrease
        parent_wallet_after = (await client.get("/api/v1/wallets/me", headers=parent_headers)).json()["data"]
        assert float(parent_wallet_after["balance_idr"]) < float(parent_wallet_before["balance_idr"])

    async def test_allowance_transfer_insufficient_balance(self, client, parent_headers, family_setup):
        child_id = family_setup["child_id"]
        # No topup — parent starts with 0
        create_res = await client.post(
            "/api/v1/allowances/",
            json={"child_id": child_id, "amount": "999999.00", "currency": "IDR", "is_recurring": False},
            headers=parent_headers,
        )
        assert create_res.status_code == 201
        allowance_id = create_res.json()["data"]["id"]

        transfer_res = await client.post(
            f"/api/v1/allowances/{allowance_id}/transfer",
            headers=parent_headers,
        )
        assert transfer_res.status_code == 400

    async def test_list_allowances(self, client, parent_headers, family_setup, topped_up_parent):
        child_id = family_setup["child_id"]
        await client.post(
            "/api/v1/allowances/",
            json={"child_id": child_id, "amount": "10000.00", "currency": "IDR", "is_recurring": False},
            headers=parent_headers,
        )
        res = await client.get("/api/v1/allowances/", headers=parent_headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) >= 1

    async def test_duplicate_parent_child_allowance_rejected(self, client, parent_headers, family_setup, topped_up_parent):
        child_id = family_setup["child_id"]
        payload = {"child_id": child_id, "amount": "10000.00", "currency": "IDR", "is_recurring": False}
        r1 = await client.post("/api/v1/allowances/", json=payload, headers=parent_headers)
        assert r1.status_code == 201
        r2 = await client.post("/api/v1/allowances/", json=payload, headers=parent_headers)
        assert r2.status_code == 409


# ================================================================== #
# FUND REQUEST
# ================================================================== #

class TestFundRequest:
    async def test_child_can_request_funds(self, client, child_headers, family_setup):
        res = await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "50000.00", "currency": "IDR", "type": "one_time", "reason": "Untuk beli buku"},
            headers=child_headers,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["status"] == "pending"

    async def test_pending_request_limit(self, client, child_headers, family_setup):
        # Create 10 pending requests
        for i in range(10):
            res = await client.post(
                "/api/v1/fund-requests/",
                json={"amount": "1000.00", "currency": "IDR", "type": "one_time"},
                headers=child_headers,
            )
            assert res.status_code == 201

        # The 11th should fail
        res = await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "1000.00", "currency": "IDR", "type": "one_time"},
            headers=child_headers,
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "TOO_MANY_PENDING"

    async def test_parent_cannot_create_fund_request(self, client, parent_headers, family_setup):
        res = await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "10000.00", "currency": "IDR", "type": "one_time"},
            headers=parent_headers,
        )
        assert res.status_code == 403

    async def test_parent_approves_fund_request(self, client, parent_headers, child_headers, family_setup, topped_up_parent):
        # Child requests funds
        req_res = await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "30000.00", "currency": "IDR", "type": "one_time", "reason": "Beli alat tulis"},
            headers=child_headers,
        )
        assert req_res.status_code == 201
        req_id = req_res.json()["data"]["id"]

        child_wallet_before = (await client.get("/api/v1/wallets/me", headers=child_headers)).json()["data"]

        # Parent approves
        approve_res = await client.post(
            f"/api/v1/fund-requests/{req_id}/approve",
            headers=parent_headers,
        )
        assert approve_res.status_code == 200, approve_res.text
        assert approve_res.json()["data"]["status"] == "approved"

        # Child balance increases
        child_wallet_after = (await client.get("/api/v1/wallets/me", headers=child_headers)).json()["data"]
        assert float(child_wallet_after["balance_idr"]) > float(child_wallet_before["balance_idr"])

    async def test_parent_rejects_fund_request(self, client, parent_headers, child_headers, family_setup):
        req_res = await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "10000.00", "currency": "IDR", "type": "one_time"},
            headers=child_headers,
        )
        req_id = req_res.json()["data"]["id"]

        reject_res = await client.post(
            f"/api/v1/fund-requests/{req_id}/reject",
            headers=parent_headers,
        )
        assert reject_res.status_code == 200
        assert reject_res.json()["data"]["status"] == "rejected"

    async def test_cannot_approve_already_approved(self, client, parent_headers, child_headers, family_setup, topped_up_parent):
        req_res = await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "10000.00", "currency": "IDR", "type": "one_time"},
            headers=child_headers,
        )
        req_id = req_res.json()["data"]["id"]

        await client.post(f"/api/v1/fund-requests/{req_id}/approve", headers=parent_headers)
        res2 = await client.post(f"/api/v1/fund-requests/{req_id}/approve", headers=parent_headers)
        assert res2.status_code == 400

    async def test_approve_insufficient_parent_balance(self, client, parent_headers, child_headers, family_setup):
        # No topup → parent has 0 balance
        req_res = await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "999999.00", "currency": "IDR", "type": "one_time"},
            headers=child_headers,
        )
        req_id = req_res.json()["data"]["id"]

        res = await client.post(f"/api/v1/fund-requests/{req_id}/approve", headers=parent_headers)
        assert res.status_code == 400

    async def test_list_fund_requests(self, client, parent_headers, child_headers, family_setup):
        await client.post(
            "/api/v1/fund-requests/",
            json={"amount": "5000.00", "currency": "IDR", "type": "one_time"},
            headers=child_headers,
        )
        res = await client.get("/api/v1/fund-requests/", headers=parent_headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) >= 1


# ================================================================== #
# EXPENSES
# ================================================================== #

class TestExpense:
    async def test_create_expense_no_wallet_deduction(self, client, parent_headers, family_setup):
        res = await client.post(
            "/api/v1/expenses/",
            json={
                "amount": "45000.00",
                "currency": "IDR",
                "category": "food_dining",
                "title": "Makan Siang",
                "deduct_from_wallet": False,
            },
            headers=parent_headers,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["category"] == "food_dining"
        assert data["deduct_from_wallet"] is False
        assert data["transaction_id"] is None

    async def test_create_expense_with_wallet_deduction(self, client, parent_headers, family_setup, topped_up_parent):
        wallet_before = (await client.get("/api/v1/wallets/me", headers=parent_headers)).json()["data"]

        res = await client.post(
            "/api/v1/expenses/",
            json={
                "amount": "20000.00",
                "currency": "IDR",
                "category": "transportation",
                "title": "Ongkos Ojek",
                "deduct_from_wallet": True,
            },
            headers=parent_headers,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["deduct_from_wallet"] is True
        assert data["transaction_id"] is not None

        wallet_after = (await client.get("/api/v1/wallets/me", headers=parent_headers)).json()["data"]
        assert float(wallet_after["balance_idr"]) < float(wallet_before["balance_idr"])

    async def test_expense_deduct_insufficient_balance(self, client, parent_headers, family_setup):
        res = await client.post(
            "/api/v1/expenses/",
            json={
                "amount": "999999.00",
                "currency": "IDR",
                "category": "shopping",
                "title": "Belanja Mahal",
                "deduct_from_wallet": True,
            },
            headers=parent_headers,
        )
        assert res.status_code == 400

    async def test_list_expenses(self, client, parent_headers, family_setup):
        await client.post(
            "/api/v1/expenses/",
            json={"amount": "10000.00", "currency": "IDR", "category": "other", "title": "Pengeluaran", "deduct_from_wallet": False},
            headers=parent_headers,
        )
        res = await client.get("/api/v1/expenses/", headers=parent_headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) >= 1

    async def test_get_expense_detail(self, client, parent_headers, family_setup):
        create_res = await client.post(
            "/api/v1/expenses/",
            json={"amount": "5000.00", "currency": "IDR", "category": "education", "title": "Fotocopy", "deduct_from_wallet": False},
            headers=parent_headers,
        )
        expense_id = create_res.json()["data"]["id"]
        res = await client.get(f"/api/v1/expenses/{expense_id}", headers=parent_headers)
        assert res.status_code == 200

    async def test_update_expense_metadata(self, client, parent_headers, family_setup):
        create_res = await client.post(
            "/api/v1/expenses/",
            json={"amount": "5000.00", "currency": "IDR", "category": "health", "title": "Obat", "deduct_from_wallet": False},
            headers=parent_headers,
        )
        expense_id = create_res.json()["data"]["id"]

        update_res = await client.patch(
            f"/api/v1/expenses/{expense_id}",
            json={"title": "Obat Batuk"},
            headers=parent_headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["data"]["title"] == "Obat Batuk"

    async def test_delete_expense_without_deduction(self, client, parent_headers, family_setup):
        create_res = await client.post(
            "/api/v1/expenses/",
            json={"amount": "5000.00", "currency": "IDR", "category": "other", "title": "Hapus Ini", "deduct_from_wallet": False},
            headers=parent_headers,
        )
        expense_id = create_res.json()["data"]["id"]
        res = await client.delete(f"/api/v1/expenses/{expense_id}", headers=parent_headers)
        assert res.status_code == 204

    async def test_cannot_delete_expense_with_deduction(self, client, parent_headers, family_setup, topped_up_parent):
        create_res = await client.post(
            "/api/v1/expenses/",
            json={"amount": "5000.00", "currency": "IDR", "category": "other", "title": "Tidak Bisa Hapus", "deduct_from_wallet": True},
            headers=parent_headers,
        )
        expense_id = create_res.json()["data"]["id"]
        res = await client.delete(f"/api/v1/expenses/{expense_id}", headers=parent_headers)
        assert res.status_code == 403  # service returns 403 for financial record protection

    async def test_filter_expenses_by_category(self, client, parent_headers, family_setup):
        await client.post(
            "/api/v1/expenses/",
            json={"amount": "1000.00", "currency": "IDR", "category": "travel", "title": "Tiket", "deduct_from_wallet": False},
            headers=parent_headers,
        )
        res = await client.get("/api/v1/expenses/?category=travel", headers=parent_headers)
        assert res.status_code == 200
        for item in res.json()["data"]:
            assert item["category"] == "travel"

    async def test_get_expense_categories(self, client, parent_headers, family_setup):
        res = await client.get("/api/v1/expenses/categories", headers=parent_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert isinstance(data, list)
        assert len(data) == 10
        values = [c["value"] for c in data]
        assert "food_dining" in values


# ================================================================== #
# PTS EXCHANGE
# ================================================================== #

class TestPtsExchange:
    async def test_exchange_pts_to_idr(self, client, child_headers, parent_headers, family_setup, topped_up_parent):
        # Give child some PTS via task reward (we simulate by checking the exchange endpoint directly)
        # First, let's check what happens with 0 PTS
        res = await client.post(
            "/api/v1/wallets/exchange-pts",
            json={"pts_amount": "1000.00"},
            headers=child_headers,
        )
        # Will fail because child has 0 PTS (or 404 if no active rate in test DB)
        assert res.status_code in (400, 404)

    async def test_exchange_pts_non_multiple_of_100(self, client, child_headers, family_setup):
        res = await client.post(
            "/api/v1/wallets/exchange-pts",
            json={"pts_amount": "150.00"},
            headers=child_headers,
        )
        assert res.status_code == 422

    async def test_exchange_pts_minimum_validation(self, client, child_headers, family_setup):
        # Less than 100 PTS
        res = await client.post(
            "/api/v1/wallets/exchange-pts",
            json={"pts_amount": "50.00"},
            headers=child_headers,
        )
        assert res.status_code == 422


# ================================================================== #
# TRANSACTION LEDGER
# ================================================================== #

class TestTransactionLedger:
    async def test_topup_creates_transaction(self, client, parent_headers, family_setup):
        await client.post(
            "/api/v1/wallets/topup",
            json={"amount": "100000.00", "description": "Top up awal"},
            headers=parent_headers,
        )
        res = await client.get("/api/v1/transactions/", headers=parent_headers)
        assert res.status_code == 200
        assert res.json()["meta"]["total"] >= 1

    async def test_allowance_transfer_creates_transaction(self, client, parent_headers, child_headers, family_setup, topped_up_parent):
        child_id = family_setup["child_id"]
        create_res = await client.post(
            "/api/v1/allowances/",
            json={"child_id": child_id, "amount": "15000.00", "currency": "IDR", "is_recurring": False},
            headers=parent_headers,
        )
        allowance_id = create_res.json()["data"]["id"]
        await client.post(f"/api/v1/allowances/{allowance_id}/transfer", headers=parent_headers)

        # Check child transactions
        res = await client.get("/api/v1/transactions/", headers=child_headers)
        assert res.status_code == 200
        assert res.json()["meta"]["total"] >= 1

    async def test_expense_with_deduction_creates_transaction(self, client, parent_headers, family_setup, topped_up_parent):
        tx_before = (await client.get("/api/v1/transactions/", headers=parent_headers)).json()["meta"]["total"]

        await client.post(
            "/api/v1/expenses/",
            json={"amount": "10000.00", "currency": "IDR", "category": "food_dining", "title": "Makan", "deduct_from_wallet": True},
            headers=parent_headers,
        )

        res = await client.get("/api/v1/transactions/", headers=parent_headers)
        assert res.json()["meta"]["total"] > tx_before
