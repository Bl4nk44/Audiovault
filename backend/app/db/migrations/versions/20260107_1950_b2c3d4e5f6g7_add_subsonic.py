"""add subsonic tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f7
Create Date: 2026-01-07 19:50:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Subsonic Auth Tokens
    op.create_table(
        "subsonic_auth_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("salt", sa.String(32), nullable=False),
        sa.Column("client_name", sa.String(100), nullable=True),
        sa.Column("client_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        "ix_subsonic_auth_tokens_user_active",
        "subsonic_auth_tokens",
        ["user_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_subsonic_auth_tokens_token",
        "subsonic_auth_tokens",
        ["token"],
        unique=False,
    )

    # Subsonic Ratings
    op.create_table(
        "subsonic_ratings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, default=0),
        sa.Column("rated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subsonic_ratings_user_track",
        "subsonic_ratings",
        ["user_id", "track_id"],
        unique=True,
    )

    # Subsonic Now Playing
    op.create_table(
        "subsonic_now_playing",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("client_name", sa.String(100), nullable=True),
        sa.Column("player_id", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("position_seconds", sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subsonic_now_playing_user",
        "subsonic_now_playing",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_subsonic_now_playing_updated",
        "subsonic_now_playing",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_subsonic_now_playing_updated", table_name="subsonic_now_playing")
    op.drop_index("ix_subsonic_now_playing_user", table_name="subsonic_now_playing")
    op.drop_table("subsonic_now_playing")

    op.drop_index("ix_subsonic_ratings_user_track", table_name="subsonic_ratings")
    op.drop_table("subsonic_ratings")

    op.drop_index("ix_subsonic_auth_tokens_token", table_name="subsonic_auth_tokens")
    op.drop_index("ix_subsonic_auth_tokens_user_active", table_name="subsonic_auth_tokens")
    op.drop_table("subsonic_auth_tokens")
