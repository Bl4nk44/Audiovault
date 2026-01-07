"""add starred tables

Revision ID: a1b2c3d4e5f7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-07 00:01:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Starred Artists
    op.create_table(
        "starred_artists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("artist_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artists.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "artist_id", name="unique_starred_artist"),
    )
    op.create_index(
        op.f("ix_starred_artists_artist_id"),
        "starred_artists",
        ["artist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_starred_artists_user_id"), "starred_artists", ["user_id"], unique=False
    )

    # Starred Albums
    op.create_table(
        "starred_albums",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("album_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["album_id"],
            ["albums.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "album_id", name="unique_starred_album"),
    )
    op.create_index(
        op.f("ix_starred_albums_album_id"), "starred_albums", ["album_id"], unique=False
    )
    op.create_index(
        op.f("ix_starred_albums_user_id"), "starred_albums", ["user_id"], unique=False
    )

    # Starred Tracks
    op.create_table(
        "starred_tracks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "track_id", name="unique_starred_track"),
    )
    op.create_index(
        op.f("ix_starred_tracks_track_id"), "starred_tracks", ["track_id"], unique=False
    )
    op.create_index(
        op.f("ix_starred_tracks_user_id"), "starred_tracks", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_starred_tracks_user_id"), table_name="starred_tracks")
    op.drop_index(op.f("ix_starred_tracks_track_id"), table_name="starred_tracks")
    op.drop_table("starred_tracks")

    op.drop_index(op.f("ix_starred_albums_user_id"), table_name="starred_albums")
    op.drop_index(op.f("ix_starred_albums_album_id"), table_name="starred_albums")
    op.drop_table("starred_albums")

    op.drop_index(op.f("ix_starred_artists_user_id"), table_name="starred_artists")
    op.drop_index(op.f("ix_starred_artists_artist_id"), table_name="starred_artists")
    op.drop_table("starred_artists")
