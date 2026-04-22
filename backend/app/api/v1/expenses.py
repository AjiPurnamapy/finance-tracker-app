"""
Expense router — endpoints untuk pencatatan pengeluaran.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.constants import ExpenseCategory
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.expense import (
    CreateExpenseRequest,
    ExpenseCategoryInfo,
    ExpenseResponse,
    UpdateExpenseRequest,
)
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("/categories", response_model=SuccessResponse)
async def get_expense_categories(
    _: User = Depends(get_current_active_user),
):
    """Return all available expense categories with human-readable labels."""
    categories = expense_service.get_categories()
    return SuccessResponse(data=categories)


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: CreateExpenseRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await expense_service.create_expense(user, data, db)
    return SuccessResponse(data=result)


@router.get("/", response_model=PaginatedResponse)
async def list_expenses(
    category: ExpenseCategory | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    results, total = await expense_service.list_expenses(
        user, db, category=category, page=page, per_page=per_page
    )
    import math
    return PaginatedResponse(
        data=results,
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=math.ceil(total / per_page) if total else 0,
        ),
    )


@router.get("/{expense_id}", response_model=SuccessResponse)
async def get_expense(
    expense_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await expense_service.get_expense(expense_id, user, db)
    return SuccessResponse(data=result)


@router.patch("/{expense_id}", response_model=SuccessResponse)
async def update_expense(
    expense_id: uuid.UUID,
    data: UpdateExpenseRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await expense_service.update_expense(expense_id, user, data, db)
    return SuccessResponse(data=result)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await expense_service.delete_expense(expense_id, user, db)
