"""v1 API router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from app.api.v1 import (
    allowances,
    auth,
    expenses,
    families,
    fund_requests,
    invitations,
    tasks,
    users,
    wallets,
    savings_goals,
    notifications,
    subscriptions,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(families.router)
api_router.include_router(invitations.router)
api_router.include_router(tasks.router)
api_router.include_router(wallets.wallet_router)
api_router.include_router(wallets.transaction_router)

# Phase 5
api_router.include_router(allowances.router)
api_router.include_router(fund_requests.router)
api_router.include_router(expenses.router)

# Phase 6
api_router.include_router(savings_goals.router, prefix="/savings-goals", tags=["Savings Goals"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
