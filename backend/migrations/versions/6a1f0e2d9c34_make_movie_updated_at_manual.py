"""make movie updated_at manual

Revision ID: 6a1f0e2d9c34
Revises: 9d2a4f6b8c10
Create Date: 2026-06-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6a1f0e2d9c34"
down_revision: str | Sequence[str] | None = "9d2a4f6b8c10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Let movie update tasks maintain movies.updated_at explicitly."""
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            existing_nullable=True,
            nullable=True,
            server_default=None,
        )

    # Old values may have been touched by non-movie updates. Reset them so the
    # next movie update writes a clean task-completion timestamp.
    op.execute("UPDATE movies SET updated_at = NULL")


def downgrade() -> None:
    """Restore the database default for newly inserted movie rows."""
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            existing_nullable=True,
            nullable=True,
            server_default=sa.text("(datetime('now', '+8 hours'))"),
        )
