"""v1 API router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from app.api.v1 import auth, families, invitations, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(families.router)
api_router.include_router(invitations.router)
