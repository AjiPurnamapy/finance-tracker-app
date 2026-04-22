"""
Wallet & Transaction endpoints.

GET  /api/v1/wallets/me                    — Get my wallet
GET  /api/v1/wallets/family/{family_id}    — Get all family wallets (parent only)
GET  /api/v1/transactions/                 — List transactions (paginated)
GET  /api/v1/transactions/{id}             — Get transaction detail
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, require_parent
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.task import TransactionResponse, WalletResponse
from app.services import transaction_service, wallet_service

wallet_router = APIRouter(prefix="/wallets", tags=["Wallets"])
transaction_router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ------------------------------------------------------------------ #
# Wallet endpoints
# ------------------------------------------------------------------ #

@wallet_router.get(
    "/me",
    response_model=SuccessResponse[WalletResponse],
    summary="Lihat saldo wallet saya",
)
async def get_my_wallet(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    wallet = await wallet_service.get_wallet(current_user, db)
    return SuccessResponse(data=wallet)


@wallet_router.get(
    "/family/{family_id}",
    response_model=SuccessResponse[list[WalletResponse]],
    summary="Lihat wallet semua anggota family (parent only)",
)
async def get_family_wallets(
    family_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_parent),
):
    wallets = await wallet_service.get_family_wallets(current_user, family_id, db)
    return SuccessResponse(data=wallets)


# ------------------------------------------------------------------ #
# Transaction endpoints
# ------------------------------------------------------------------ #

@transaction_router.get(
    "/",
    response_model=PaginatedResponse[TransactionResponse],
    summary="Lihat riwayat transaksi (paginated)",
)
async def list_transactions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    transactions, total = await transaction_service.list_transactions(
        current_user, db, page=page, per_page=per_page
    )
    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=transactions,
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


@transaction_router.get(
    "/{transaction_id}",
    response_model=SuccessResponse[TransactionResponse],
    summary="Lihat detail transaksi",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tx = await transaction_service.get_transaction(transaction_id, current_user, db)
    return SuccessResponse(data=tx)
