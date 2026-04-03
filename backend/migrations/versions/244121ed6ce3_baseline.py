"""baseline

Revision ID: 244121ed6ce3
Revises:
Create Date: 2026-04-08 21:05:45.559438

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "244121ed6ce3"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
