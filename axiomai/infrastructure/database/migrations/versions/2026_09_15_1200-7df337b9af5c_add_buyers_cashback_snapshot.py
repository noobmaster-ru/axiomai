"""add buyers.cashback_percent and buyers.instruction_text

Revision ID: 7df337b9af5c
Revises: a7c31f5e8d02
Create Date: 2026-09-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7df337b9af5c"
down_revision: str | Sequence[str] | None = "a7c31f5e8d02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "buyers",
        sa.Column(
            "cashback_percent",
            sa.Integer(),
            nullable=True,
            comment="Процент кэшбека, зафиксированный при создании заявки (из артикула на тот момент)",
        ),
    )
    op.add_column(
        "buyers",
        sa.Column(
            "instruction_text",
            sa.Text(),
            nullable=True,
            comment="Инструкция артикула, зафиксированная при создании заявки",
        ),
    )

    # Бэкфилл старых заявок текущими значениями их артикула — единственное, что есть на этот момент.
    # Заявкам, стартовавшим до правки процента в таблице, значение нужно поправить руками после миграции.
    op.execute(
        """
        UPDATE buyers AS b
        SET cashback_percent = a.cashback_percent,
            instruction_text = a.instruction_text
        FROM (
            SELECT DISTINCT ON (cabinet_id, nm_id) cabinet_id, nm_id, cashback_percent, instruction_text
            FROM articles
            ORDER BY cabinet_id, nm_id, is_deleted, id DESC
        ) AS a
        WHERE a.cabinet_id = b.cabinet_id AND a.nm_id = b.nm_id
        """
    )
    # Заявки без артикула в БД (в норме таких нет): 0% — автовыплата по ним ничего не начислит, как и раньше
    op.execute("UPDATE buyers SET cashback_percent = 0 WHERE cashback_percent IS NULL")
    op.execute("UPDATE buyers SET instruction_text = '' WHERE instruction_text IS NULL")

    op.alter_column("buyers", "cashback_percent", nullable=False)
    op.alter_column("buyers", "instruction_text", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("buyers", "instruction_text")
    op.drop_column("buyers", "cashback_percent")
