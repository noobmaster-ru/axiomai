"""add articles.price

Revision ID: a7c31f5e8d02
Revises: b41c7e2f9d10
Create Date: 2026-09-10 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c31f5e8d02"
down_revision: str | Sequence[str] | None = "b41c7e2f9d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "articles",
        sa.Column("price", sa.Integer(), nullable=True, comment="Цена на ВБ в рублях, из колонки K таблицы"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("articles", "price")
