"""
Invite code utility.

Generates a 6-digit numeric string (000000–999999).
Checks uniqueness against ALL existing codes in DB before returning.
"""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation


async def generate_unique_invite_code(db: AsyncSession, max_retries: int = 10) -> str:
    """
    Generate a unique 6-digit numeric invite code.

    Uses ``secrets`` (CSPRNG) for unpredictable codes.
    Checks uniqueness against ALL existing invite codes regardless of status,
    to avoid IntegrityError from the UNIQUE constraint on invite_code column.

    Collision probability: 1/1,000,000 per attempt.
    Returns plain string like '042817'.
    Raises RuntimeError only if all retries are exhausted.
    """
    for _ in range(max_retries):
        code = f"{secrets.randbelow(1_000_000):06d}"

        # Check against ALL codes in DB — column has UNIQUE constraint
        existing = await db.scalar(
            select(Invitation.id).where(Invitation.invite_code == code)
        )
        if not existing:
            return code

    raise RuntimeError(
        "Failed to generate unique invite code after max retries. "
        "This indicates the code space is becoming saturated."
    )
