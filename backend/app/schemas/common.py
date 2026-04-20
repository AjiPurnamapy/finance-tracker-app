"""
Common Pydantic v2 schemas shared across all endpoints.
Provides consistent API response envelopes.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ------------------------------------------------------------------ #
# Error schemas
# ------------------------------------------------------------------ #

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


# ------------------------------------------------------------------ #
# Success schemas
# ------------------------------------------------------------------ #

class SuccessResponse(BaseModel, Generic[T]):
    """
    Generic success envelope.

    Usage:
        SuccessResponse[UserResponse](data=user)
    """
    success: bool = True
    data: T


# ------------------------------------------------------------------ #
# Pagination
# ------------------------------------------------------------------ #

class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints."""
    page: int = Field(default=1, ge=1, description="Page number (starts at 1)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int

    @classmethod
    def from_params(cls, params: PaginationParams, total: int) -> "PaginationMeta":
        import math
        return cls(
            page=params.page,
            per_page=params.per_page,
            total=total,
            total_pages=math.ceil(total / params.per_page) if total > 0 else 0,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response envelope.

    Usage:
        PaginatedResponse[TaskResponse](data=tasks, meta=meta)
    """
    success: bool = True
    data: list[T]
    meta: PaginationMeta


# ------------------------------------------------------------------ #
# Empty state meta (for frontend UX)
# ------------------------------------------------------------------ #

class EmptyStateMeta(BaseModel):
    """
    Extra metadata returned when a list endpoint has no data.
    Helps frontend render appropriate empty state UI.
    """
    is_empty: bool = True
    empty_title: str
    empty_message: str
    empty_action: str | None = None  # e.g. "create_task", "connect_parent"
