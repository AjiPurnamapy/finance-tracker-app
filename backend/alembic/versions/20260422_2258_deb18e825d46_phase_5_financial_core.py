"""phase_5_financial_core

Revision ID: deb18e825d46
Revises: d4f30616b6f8
Create Date: 2026-04-22 22:58:48.896861
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum


revision: str = 'deb18e825d46'
down_revision: Union[str, None] = 'd4f30616b6f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Existing enum types (already created in Phase 4 migration)
# create_type=False tells SQLAlchemy NOT to CREATE TYPE
currency_enum = PgEnum('IDR', 'PTS', name='currency', create_type=False)
recurrencetype_enum = PgEnum('DAILY', 'WEEKLY', 'CUSTOM', name='recurrencetype', create_type=False)

# Phase 5 enum types — use create_type=False and create manually with IF NOT EXISTS
expensecategory_enum = PgEnum(
    'FOOD_DINING', 'TRANSPORTATION', 'HOUSING', 'SHOPPING',
    'TRAVEL', 'FAMILY', 'ENTERTAINMENT', 'EDUCATION', 'HEALTH', 'OTHER',
    name='expensecategory', create_type=False,
)
fundrequesttype_enum = PgEnum('RECURRING', 'ONE_TIME', name='fundrequesttype', create_type=False)
fundrequeststatus_enum = PgEnum('PENDING', 'APPROVED', 'REJECTED', name='fundrequeststatus', create_type=False)


def upgrade() -> None:
    # Create new enum types for Phase 5 using IF NOT EXISTS (idempotent)
    conn = op.get_bind()
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "  CREATE TYPE expensecategory AS ENUM "
        "    ('FOOD_DINING','TRANSPORTATION','HOUSING','SHOPPING','TRAVEL','FAMILY','ENTERTAINMENT','EDUCATION','HEALTH','OTHER'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "  CREATE TYPE fundrequesttype AS ENUM ('RECURRING','ONE_TIME'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "  CREATE TYPE fundrequeststatus AS ENUM ('PENDING','APPROVED','REJECTED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))

    op.create_table('pts_exchange_rates',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('pts_amount', sa.DECIMAL(precision=12, scale=2), nullable=False),
    sa.Column('idr_amount', sa.DECIMAL(precision=12, scale=2), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pts_exchange_rates_is_active'), 'pts_exchange_rates', ['is_active'], unique=False)

    op.create_table('allowances',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('family_id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('child_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.DECIMAL(precision=12, scale=2), nullable=False),
    sa.Column('currency', currency_enum, nullable=False),
    sa.Column('is_recurring', sa.Boolean(), nullable=False),
    sa.Column('recurrence_type', recurrencetype_enum, nullable=True),
    sa.Column('next_payment_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['child_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('parent_id', 'child_id', name='uq_allowance_parent_child')
    )
    op.create_index('ix_allowances_active_next_payment', 'allowances', ['is_active', 'next_payment_at'], unique=False)
    op.create_index(op.f('ix_allowances_child_id'), 'allowances', ['child_id'], unique=False)
    op.create_index(op.f('ix_allowances_family_id'), 'allowances', ['family_id'], unique=False)

    op.create_table('expenses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('family_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('wallet_id', sa.Uuid(), nullable=True),
    sa.Column('amount', sa.DECIMAL(precision=12, scale=2), nullable=False),
    sa.Column('currency', currency_enum, nullable=False),
    sa.Column('category', expensecategory_enum, nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('spent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('deduct_from_wallet', sa.Boolean(), nullable=False),
    sa.Column('transaction_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expenses_category'), 'expenses', ['category'], unique=False)
    op.create_index(op.f('ix_expenses_family_id'), 'expenses', ['family_id'], unique=False)
    op.create_index('ix_expenses_family_spent_at', 'expenses', ['family_id', 'spent_at'], unique=False)
    op.create_index(op.f('ix_expenses_user_id'), 'expenses', ['user_id'], unique=False)
    op.create_index('ix_expenses_user_spent_at', 'expenses', ['user_id', 'spent_at'], unique=False)

    op.create_table('fund_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('family_id', sa.Uuid(), nullable=False),
    sa.Column('child_id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=True),
    sa.Column('amount', sa.DECIMAL(precision=12, scale=2), nullable=False),
    sa.Column('currency', currency_enum, nullable=False),
    sa.Column('type', fundrequesttype_enum, nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=True),
    sa.Column('status', fundrequeststatus_enum, nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('transaction_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['child_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fund_requests_child_id'), 'fund_requests', ['child_id'], unique=False)
    op.create_index('ix_fund_requests_child_status', 'fund_requests', ['child_id', 'status'], unique=False)
    op.create_index(op.f('ix_fund_requests_family_id'), 'fund_requests', ['family_id'], unique=False)
    op.create_index('ix_fund_requests_family_status', 'fund_requests', ['family_id', 'status'], unique=False)
    op.create_index(op.f('ix_fund_requests_status'), 'fund_requests', ['status'], unique=False)

    # ------------------------------------------------------------------ #
    # Seed: default PTS exchange rate — 1000 PTS = Rp 10.000
    # ------------------------------------------------------------------ #
    import uuid as _uuid
    from datetime import datetime, UTC

    seed_id = str(_uuid.uuid4())
    seed_now = datetime.now(UTC).isoformat()
    conn = op.get_bind()
    conn.execute(
        sa.text(
            f"INSERT INTO pts_exchange_rates (id, pts_amount, idr_amount, is_active, created_by, created_at, updated_at) "
            f"VALUES ('{seed_id}'::uuid, 1000.00, 10000.00, true, NULL, '{seed_now}'::timestamptz, '{seed_now}'::timestamptz)"
        )
    )



def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_fund_requests_status'), table_name='fund_requests')
    op.drop_index('ix_fund_requests_family_status', table_name='fund_requests')
    op.drop_index(op.f('ix_fund_requests_family_id'), table_name='fund_requests')
    op.drop_index('ix_fund_requests_child_status', table_name='fund_requests')
    op.drop_index(op.f('ix_fund_requests_child_id'), table_name='fund_requests')
    op.drop_table('fund_requests')
    op.drop_index('ix_expenses_user_spent_at', table_name='expenses')
    op.drop_index(op.f('ix_expenses_user_id'), table_name='expenses')
    op.drop_index('ix_expenses_family_spent_at', table_name='expenses')
    op.drop_index(op.f('ix_expenses_family_id'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_category'), table_name='expenses')
    op.drop_table('expenses')
    op.drop_index(op.f('ix_allowances_family_id'), table_name='allowances')
    op.drop_index(op.f('ix_allowances_child_id'), table_name='allowances')
    op.drop_index('ix_allowances_active_next_payment', table_name='allowances')
    op.drop_table('allowances')
    op.drop_index(op.f('ix_pts_exchange_rates_is_active'), table_name='pts_exchange_rates')
    op.drop_table('pts_exchange_rates')
    # ### end Alembic commands ###
