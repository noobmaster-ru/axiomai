"""add articles.cashback_percent

Revision ID: 2d88927e1285
Revises: 60a58617f239
Create Date: 2026-03-10 10:36:22.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2d88927e1285"
down_revision: str | Sequence[str] | None = "60a58617f239"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("articles", sa.Column("cashback_percent", sa.Integer(), nullable=False, server_default="100"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("articles", "cashback_percent")
