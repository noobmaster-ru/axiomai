"""add indexes and balance notification unique constraint

Revision ID: b41c7e2f9d10
Revises: 2d88927e1285
Create Date: 2026-08-31 12:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "b41c7e2f9d10"
down_revision = "2d88927e1285"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_buyers_telegram_id_cabinet_id", "buyers", ["telegram_id", "cabinet_id"])
    op.create_index(op.f("ix_buyers_cabinet_id"), "buyers", ["cabinet_id"])
    op.create_index(op.f("ix_buyers_nm_id"), "buyers", ["nm_id"])
    op.create_index(op.f("ix_cashback_tables_cabinet_id"), "cashback_tables", ["cabinet_id"])
    op.create_index(op.f("ix_articles_cabinet_id"), "articles", ["cabinet_id"])
    op.create_index(op.f("ix_articles_nm_id"), "articles", ["nm_id"])
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"])
    op.create_index(op.f("ix_payments_cashback_table_id"), "payments", ["cashback_table_id"])

    # Дедупликация перед unique: оставляем самое раннее уведомление каждого порога
    op.execute(
        sa.text(
            """
            DELETE FROM balance_notifications bn
            USING balance_notifications older
            WHERE bn.cabinet_id = older.cabinet_id
              AND bn.initial_balance = older.initial_balance
              AND bn.threshold = older.threshold
              AND bn.id > older.id
            """
        )
    )
    op.create_unique_constraint(
        "uq_balance_notifications_cycle_threshold",
        "balance_notifications",
        ["cabinet_id", "initial_balance", "threshold"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_balance_notifications_cycle_threshold", "balance_notifications", type_="unique")
    op.drop_index(op.f("ix_payments_cashback_table_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_index(op.f("ix_articles_nm_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_cabinet_id"), table_name="articles")
    op.drop_index(op.f("ix_cashback_tables_cabinet_id"), table_name="cashback_tables")
    op.drop_index(op.f("ix_buyers_nm_id"), table_name="buyers")
    op.drop_index(op.f("ix_buyers_cabinet_id"), table_name="buyers")
    op.drop_index(op.f("ix_buyers_telegram_id_cabinet_id"), table_name="buyers")
