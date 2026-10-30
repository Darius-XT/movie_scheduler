"""Add mutually exclusive skipped label to movies."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8e2f4a6b901"
down_revision: str | Sequence[str] | None = "6a1f0e2d9c34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("movies") as batch:
        batch.add_column(sa.Column("is_skipped", sa.Boolean(), nullable=False, server_default="0"))
        batch.create_check_constraint("ck_movies_exclusive_label", "NOT (is_wished AND is_skipped)")


def downgrade() -> None:
    with op.batch_alter_table("movies") as batch:
        batch.drop_constraint("ck_movies_exclusive_label", type_="check")
        batch.drop_column("is_skipped")
