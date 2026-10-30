"""Persist explicit movie viewing location."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b5c7d9e234"
down_revision: str | Sequence[str] | None = "f0a4b6c8d123"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("movies") as batch:
        batch.add_column(sa.Column("viewing_location", sa.String(20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("movies") as batch:
        batch.drop_column("viewing_location")
