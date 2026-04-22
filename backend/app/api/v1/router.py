"""v1 API router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from app.api.v1 import auth, families, invitations, tasks, users, wallets

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(families.router)
api_router.include_router(invitations.router)
api_router.include_router(tasks.router)
api_router.include_router(wallets.wallet_router)
api_router.include_router(wallets.transaction_router)
