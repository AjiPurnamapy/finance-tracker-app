"""
Application-wide enums and constants.
All enums used by SQLAlchemy models are defined here to avoid circular imports.
"""

from enum import Enum


# ------------------------------------------------------------------ #
# User & Auth
# ------------------------------------------------------------------ #

class UserRole(str, Enum):
    PARENT = "parent"
    CHILD = "child"


class FamilyMemberRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


# ------------------------------------------------------------------ #
# Invitation
# ------------------------------------------------------------------ #

class InvitationStatus(str, Enum):
    SENT = "sent"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# ------------------------------------------------------------------ #
# Task
# ------------------------------------------------------------------ #

class TaskStatus(str, Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class RecurrenceType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


# ------------------------------------------------------------------ #
# Financial
# ------------------------------------------------------------------ #

class Currency(str, Enum):
    IDR = "IDR"
    PTS = "PTS"


class TransactionType(str, Enum):
    ALLOWANCE = "allowance"
    TASK_REWARD = "task_reward"
    BONUS = "bonus"
    EXPENSE = "expense"
    PTS_EXCHANGE = "pts_exchange"
    SUBSCRIPTION = "subscription"
    TOPUP = "topup"
    FUND_REQUEST = "fund_request"


class FundRequestType(str, Enum):
    RECURRING = "recurring"
    ONE_TIME = "one_time"


class FundRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ------------------------------------------------------------------ #
# Expense
# ------------------------------------------------------------------ #

class ExpenseCategory(str, Enum):
    FOOD_DINING = "food_dining"
    TRANSPORTATION = "transportation"
    HOUSING = "housing"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    FAMILY = "family"
    ENTERTAINMENT = "entertainment"
    EDUCATION = "education"
    HEALTH = "health"
    OTHER = "other"


# Human-readable labels for each category (used in API responses)
EXPENSE_CATEGORY_LABELS: dict[ExpenseCategory, str] = {
    ExpenseCategory.FOOD_DINING: "Makanan & Minuman",
    ExpenseCategory.TRANSPORTATION: "Transportasi",
    ExpenseCategory.HOUSING: "Rumah & Utilitas",
    ExpenseCategory.SHOPPING: "Belanja",
    ExpenseCategory.TRAVEL: "Liburan & Travel",
    ExpenseCategory.FAMILY: "Keluarga",
    ExpenseCategory.ENTERTAINMENT: "Hiburan",
    ExpenseCategory.EDUCATION: "Pendidikan",
    ExpenseCategory.HEALTH: "Kesehatan",
    ExpenseCategory.OTHER: "Lainnya",
}


# ------------------------------------------------------------------ #
# Subscription
# ------------------------------------------------------------------ #

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"


# Max seats per subscription tier
SUBSCRIPTION_MAX_SEATS: dict[SubscriptionTier, int] = {
    SubscriptionTier.FREE: 2,   # 1 parent + 1 child
    SubscriptionTier.PRO: 6,    # 1 parent + 5 children
}


# ------------------------------------------------------------------ #
# Notification
# ------------------------------------------------------------------ #

class NotificationType(str, Enum):
    TASK_APPROVED = "task_approved"
    TASK_REJECTED = "task_rejected"
    TASK_SUBMITTED = "task_submitted"
    ALLOWANCE_RECEIVED = "allowance_received"
    FUND_REQUEST = "fund_request"
    FUND_APPROVED = "fund_approved"
    FUND_REJECTED = "fund_rejected"
    GOAL_MILESTONE = "goal_milestone"
    INVITATION = "invitation"
    MEMBER_JOINED = "member_joined"
    SYSTEM = "system"
