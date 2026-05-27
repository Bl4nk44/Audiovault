"""Add missing track columns (musicbrainz_id, soundcloud_id, metadata_source, metadata_confidence)

Revision ID: b3f8c9d0e1a2
Revises: a5d7f8e81880
Create Date: 2026-03-05 12:46:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f8c9d0e1a2"
down_revision: str | None = "a5d7f8e81880"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tracks", sa.Column("musicbrainz_id", sa.String(length=100), nullable=True))
    op.add_column("tracks", sa.Column("soundcloud_id", sa.String(length=100), nullable=True))
    op.add_column("tracks", sa.Column("metadata_source", sa.String(length=50), nullable=True))
    op.add_column("tracks", sa.Column("metadata_confidence", sa.Float(), nullable=True, server_default="1.0"))

    op.create_unique_constraint("uq_tracks_musicbrainz_id", "tracks", ["musicbrainz_id"])
    op.create_unique_constraint("uq_tracks_soundcloud_id", "tracks", ["soundcloud_id"])


def downgrade() -> None:
    op.drop_constraint("uq_tracks_soundcloud_id", "tracks", type_="unique")
    op.drop_constraint("uq_tracks_musicbrainz_id", "tracks", type_="unique")

    op.drop_column("tracks", "metadata_confidence")
    op.drop_column("tracks", "metadata_source")
    op.drop_column("tracks", "soundcloud_id")
    op.drop_column("tracks", "musicbrainz_id")
