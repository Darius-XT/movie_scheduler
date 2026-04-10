"""add douban_url to movies

Revision ID: 8c0f4f7f4ab1
Revises: 12c446c6303d
Create Date: 2026-04-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c0f4f7f4ab1"
down_revision: str | Sequence[str] | None = "12c446c6303d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("douban_url", sa.String(length=255), nullable=True, comment="豆瓣详情链接"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("movies", schema=None) as batch_op:
        batch_op.drop_column("douban_url")
