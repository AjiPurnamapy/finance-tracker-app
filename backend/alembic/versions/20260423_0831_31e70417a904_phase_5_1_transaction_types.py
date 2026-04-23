"""phase_5_1_transaction_types

Revision ID: 31e70417a904
Revises: deb18e825d46
Create Date: 2026-04-23 08:31:09.615253
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '31e70417a904'
down_revision: Union[str, None] = 'deb18e825d46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.engine.name == "postgresql":
        # Add new enum values if they don't exist
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'topup'")
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'fund_request'")


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values easily (ALTER TYPE ... DROP VALUE does not exist).
    # Since these are just new values, we can leave them in the DB.
    # If a strict downgrade is required, we would have to create a new enum, update the table, and drop the old enum.
    pass
