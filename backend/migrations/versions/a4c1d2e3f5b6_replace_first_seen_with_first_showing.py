"""replace first_seen_at with first_showing_at

Revision ID: a4c1d2e3f5b6
Revises: b3e9f2a17c84
Create Date: 2026-04-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4c1d2e3f5b6"
down_revision: str | Sequence[str] | None = "b3e9f2a17c84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "first_showing_at",
                sa.DateTime(),
                nullable=True,
                comment="最近一次进入正在热映状态的时间（北京时间）",
            )
        )

    # 回填：is_showing=1 的电影用 first_seen_at 作为近似初值，避免上线瞬间排序断崖
    op.execute("UPDATE movies SET first_showing_at = first_seen_at WHERE is_showing = 1")

    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.drop_column("first_seen_at")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "first_seen_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("datetime('now', '+8 hours')"),
                comment="首次抓取时间（北京时间，不随更新变化）",
            )
        )
        batch_op.drop_column("first_showing_at")
