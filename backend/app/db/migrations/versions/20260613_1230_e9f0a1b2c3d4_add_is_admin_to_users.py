"""add is_admin to users

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-06-13 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Backfill: the bootstrap admin account (username "admin") becomes a real admin.
    op.execute("UPDATE users SET is_admin = true WHERE username = 'admin'")


def downgrade() -> None:
    op.drop_column("users", "is_admin")
