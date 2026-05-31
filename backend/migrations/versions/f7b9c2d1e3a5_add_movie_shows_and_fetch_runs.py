"""add movie_shows and show_fetch_runs tables

Revision ID: f7b9c2d1e3a5
Revises: e5f7a9c1d2b4
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7b9c2d1e3a5"
down_revision: str | Sequence[str] | None = "e5f7a9c1d2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: 新增场次表与场次抓取任务元信息表。"""
    op.create_table(
        "movie_shows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="场次ID"),
        sa.Column("movie_id", sa.Integer(), nullable=False, comment="电影ID"),
        sa.Column("cinema_id", sa.Integer(), nullable=False, comment="影院ID"),
        sa.Column("cinema_name", sa.String(length=200), nullable=False, comment="影院名称(快照)"),
        sa.Column("date", sa.String(length=20), nullable=False, comment="放映日期"),
        sa.Column("time", sa.String(length=20), nullable=False, comment="放映时间"),
        sa.Column("price", sa.String(length=20), nullable=True, comment="票价"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("datetime('now', '+8 hours')"),
            nullable=False,
            comment="创建时间(北京时间)",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "movie_id", "cinema_id", "date", "time",
            name="uq_movie_shows_movie_cinema_date_time",
        ),
    )
    op.create_index(op.f("ix_movie_shows_movie_id"), "movie_shows", ["movie_id"], unique=False)
    op.create_index(op.f("ix_movie_shows_cinema_id"), "movie_shows", ["cinema_id"], unique=False)
    op.create_index(op.f("ix_movie_shows_date"), "movie_shows", ["date"], unique=False)

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


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("show_fetch_runs")
    op.drop_index(op.f("ix_movie_shows_date"), table_name="movie_shows")
    op.drop_index(op.f("ix_movie_shows_cinema_id"), table_name="movie_shows")
    op.drop_index(op.f("ix_movie_shows_movie_id"), table_name="movie_shows")
    op.drop_table("movie_shows")
