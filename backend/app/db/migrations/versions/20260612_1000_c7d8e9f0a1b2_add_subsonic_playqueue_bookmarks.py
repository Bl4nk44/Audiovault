"""add subsonic play queue and bookmarks

Revision ID: c7d8e9f0a1b2
Revises: 1f61e95eab95
Create Date: 2026-06-12 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "1f61e95eab95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subsonic_play_queues",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("track_ids", sa.JSON(), nullable=False),
        sa.Column("current_track_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("position_ms", sa.Integer(), nullable=False),
        sa.Column("changed_by", sa.String(length=100), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_track_id"], ["tracks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_subsonic_play_queues_user", "subsonic_play_queues", ["user_id"], unique=True)

    op.create_table(
        "subsonic_bookmarks",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("track_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("position_ms", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subsonic_bookmarks_user_track", "subsonic_bookmarks", ["user_id", "track_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_subsonic_bookmarks_user_track", table_name="subsonic_bookmarks")
    op.drop_table("subsonic_bookmarks")
    op.drop_index("ix_subsonic_play_queues_user", table_name="subsonic_play_queues")
    op.drop_table("subsonic_play_queues")
