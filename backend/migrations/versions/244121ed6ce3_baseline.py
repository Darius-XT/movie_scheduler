"""baseline

Revision ID: 244121ed6ce3
Revises:
Create Date: 2026-04-08 21:05:45.559438

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "244121ed6ce3"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True, comment="电影ID"),
        sa.Column("title", sa.String(200), nullable=False, comment="电影标题"),
        sa.Column("score", sa.String(10), nullable=True, comment="完整评分"),
        sa.Column("genres", sa.Text(), nullable=True, comment="电影类型"),
        sa.Column("actors", sa.Text(), nullable=True, comment="主演"),
        sa.Column("release_date", sa.String(20), nullable=True, comment="上映日期"),
        sa.Column("release_year", sa.String(10), nullable=True, comment="上映年份"),
        sa.Column("is_showing", sa.Boolean(), nullable=False, server_default="0", comment="是否正在热映"),
        sa.Column("director", sa.Text(), nullable=True, comment="导演"),
        sa.Column("country", sa.String(100), nullable=True, comment="制片国家"),
        sa.Column("language", sa.String(100), nullable=True, comment="语言"),
        sa.Column("duration", sa.String(20), nullable=True, comment="时长"),
        sa.Column("description", sa.Text(), nullable=True, comment="剧情简介"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(datetime('now', '+8 hours'))")),
    )

    op.create_table(
        "cinemas",
        sa.Column("id", sa.Integer(), primary_key=True, comment="影院ID"),
        sa.Column("name", sa.String(200), nullable=False, comment="影院名称"),
        sa.Column("address", sa.String(500), nullable=False, comment="影院地址"),
        sa.Column("price", sa.String(20), nullable=True, comment="票价"),
        sa.Column("allow_refund", sa.Boolean(), nullable=True, comment="是否允许退票"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(datetime('now', '+8 hours'))")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("cinemas")
    op.drop_table("movies")
