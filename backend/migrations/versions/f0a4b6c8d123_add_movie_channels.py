"""Persist movie viewing channels."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f0a4b6c8d123"
down_revision: str | Sequence[str] | None = "e9f3a5b7c012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("movies") as batch:
        batch.add_column(sa.Column("channels", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("movies") as batch:
        batch.drop_column("channels")
