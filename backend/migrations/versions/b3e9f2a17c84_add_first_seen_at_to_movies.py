"""add first_seen_at to movies

Revision ID: b3e9f2a17c84
Revises: 8c0f4f7f4ab1
Create Date: 2026-04-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3e9f2a17c84"
down_revision: str | Sequence[str] | None = "8c0f4f7f4ab1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
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


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.drop_column("first_seen_at")
