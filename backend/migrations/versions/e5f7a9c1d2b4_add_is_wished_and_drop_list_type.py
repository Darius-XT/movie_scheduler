"""add is_wished column and drop planning_items.list_type

Revision ID: e5f7a9c1d2b4
Revises: c7d8e9f0a1b2
Create Date: 2026-05-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f7a9c1d2b4"
down_revision: str | Sequence[str] | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: movies 加 is_wished;清空 planning_items 的旧 wish 行;删 list_type 列与相关约束。"""
    with op.batch_alter_table("movies") as batch:
        batch.add_column(
            sa.Column(
                "is_wished",
                sa.Boolean(),
                nullable=False,
                server_default="0",
                comment="是否加入想看",
            )
        )

    op.execute("DELETE FROM planning_items WHERE list_type = 'wish'")

    with op.batch_alter_table("planning_items") as batch:
        batch.drop_index("ix_planning_items_list_type")
        batch.drop_constraint("uq_planning_items_list_type_show_key", type_="unique")
        batch.drop_column("list_type")
        batch.create_unique_constraint("uq_planning_items_show_key", ["show_key"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("planning_items") as batch:
        batch.drop_constraint("uq_planning_items_show_key", type_="unique")
        batch.add_column(
            sa.Column(
                "list_type",
                sa.String(length=20),
                nullable=False,
                server_default="schedule",
                comment="列表类型：wish 或 schedule",
            )
        )
        batch.create_index("ix_planning_items_list_type", ["list_type"], unique=False)
        batch.create_unique_constraint(
            "uq_planning_items_list_type_show_key", ["list_type", "show_key"]
        )

    with op.batch_alter_table("movies") as batch:
        batch.drop_column("is_wished")
