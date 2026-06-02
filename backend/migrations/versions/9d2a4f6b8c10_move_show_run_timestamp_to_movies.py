"""move show run timestamp to movies

Revision ID: 9d2a4f6b8c10
Revises: f7b9c2d1e3a5
Create Date: 2026-06-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9d2a4f6b8c10"
down_revision: str | Sequence[str] | None = "f7b9c2d1e3a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: 用 movies.shows_updated_at 替代 show_fetch_runs。"""
    with op.batch_alter_table("movies") as batch:
        batch.add_column(
            sa.Column(
                "shows_updated_at",
                sa.DateTime(),
                nullable=True,
                comment="场次最近一次刷新完成时间（北京时间）",
            )
        )

    op.execute(
        """
        UPDATE movies
        SET shows_updated_at = (
            SELECT MAX(finished_at)
            FROM show_fetch_runs
            WHERE finished_at IS NOT NULL
        )
        WHERE is_wished = 1
          AND EXISTS (
            SELECT 1
            FROM show_fetch_runs
            WHERE finished_at IS NOT NULL
          )
        """
    )

    op.drop_table("show_fetch_runs")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "show_fetch_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="任务ID"),
        sa.Column("started_at", sa.DateTime(), nullable=False, comment="开始时间"),
        sa.Column("finished_at", sa.DateTime(), nullable=True, comment="完成时间"),
        sa.Column("movie_count", sa.Integer(), server_default="0", nullable=False, comment="电影数量"),
        sa.Column("success_count", sa.Integer(), server_default="0", nullable=False, comment="成功数"),
        sa.Column("error", sa.String(length=500), nullable=True, comment="失败原因"),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("movies") as batch:
        batch.drop_column("shows_updated_at")
