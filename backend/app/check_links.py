
import asyncio
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.models.track import Track
from app.models.artist import Artist
from app.models.album import Album
from app.models.download import Download

async def check_links():
    async with AsyncSessionLocal() as db:
        # Total tracks
        tracks_count = await db.execute(select(func.count(Track.id)))
        total = tracks_count.scalar()
        print(f"Total Tracks: {total}")

        # Unlinked tracks
        no_artist = await db.execute(select(func.count(Track.id)).where(Track.artist_id.is_(None)))
        no_album = await db.execute(select(func.count(Track.id)).where(Track.album_id.is_(None)))
        print(f"Tracks without Artist: {no_artist.scalar()}")
        print(f"Tracks without Album: {no_album.scalar()}")

        # Tracks with completed downloads
        completed_dl = await db.execute(
            select(Track)
            .join(Download, Download.track_id == Track.id)
            .where(Download.status == 'completed')
        )
        dl_tracks = completed_dl.scalars().all()
        print(f"Tracks with completed downloads: {len(dl_tracks)}")

        # Check if those tracks have artists
        dl_unlinked = 0
        for track in dl_tracks:
            if track.artist_id is None:
                dl_unlinked += 1
        print(f"Downloaded tracks without Artist: {dl_unlinked}")

        # Artist count
        artists = await db.execute(select(func.count(Artist.id)))
        print(f"Total Artists: {artists.scalar()}")

        # Album count
        albums = await db.execute(select(func.count(Album.id)))
        print(f"Total Albums: {albums.scalar()}")

if __name__ == "__main__":
    asyncio.run(check_links())
