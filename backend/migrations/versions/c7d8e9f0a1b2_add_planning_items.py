"""add planning items

Revision ID: c7d8e9f0a1b2
Revises: a4c1d2e3f5b6
Create Date: 2026-05-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | Sequence[str] | None = "a4c1d2e3f5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "planning_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="计划条目ID"),
        sa.Column("list_type", sa.String(length=20), nullable=False, comment="列表类型：wish 或 schedule"),
        sa.Column("show_key", sa.String(length=255), nullable=False, comment="前端场次唯一键"),
        sa.Column("movie_id", sa.Integer(), nullable=False, comment="电影ID"),
        sa.Column("movie_title", sa.String(length=200), nullable=False, comment="电影标题"),
        sa.Column("date", sa.String(length=20), nullable=False, comment="放映日期"),
        sa.Column("time", sa.String(length=20), nullable=False, comment="放映时间"),
        sa.Column("cinema_id", sa.Integer(), nullable=False, comment="影院ID"),
        sa.Column("cinema_name", sa.String(length=200), nullable=False, comment="影院名称"),
        sa.Column("price", sa.String(length=20), nullable=True, comment="票价"),
        sa.Column("duration_minutes", sa.Integer(), nullable=True, comment="片长分钟数"),
        sa.Column("purchased", sa.Boolean(), server_default="0", nullable=False, comment="是否已购票"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("datetime('now', '+8 hours')"),
            nullable=False,
            comment="创建时间（北京时间）",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("datetime('now', '+8 hours')"),
            nullable=False,
            comment="更新时间（北京时间）",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("list_type", "show_key", name="uq_planning_items_list_type_show_key"),
    )
    op.create_index(op.f("ix_planning_items_cinema_id"), "planning_items", ["cinema_id"], unique=False)
    op.create_index(op.f("ix_planning_items_date"), "planning_items", ["date"], unique=False)
    op.create_index(op.f("ix_planning_items_list_type"), "planning_items", ["list_type"], unique=False)
    op.create_index(op.f("ix_planning_items_movie_id"), "planning_items", ["movie_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_planning_items_movie_id"), table_name="planning_items")
    op.drop_index(op.f("ix_planning_items_list_type"), table_name="planning_items")
    op.drop_index(op.f("ix_planning_items_date"), table_name="planning_items")
    op.drop_index(op.f("ix_planning_items_cinema_id"), table_name="planning_items")
    op.drop_table("planning_items")
