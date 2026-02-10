import asyncio

from app.services.lyrics_service import lyrics_service


async def test_song(artist, title):
    print(f"\n--- Testing: {artist} - {title} ---")
    try:
        # Try once with cache
        print("Attempt 1 (with cache):")
        data = await lyrics_service.get_lyrics(artist, title, use_cache=True)
        print(f"Found: {data.get('found')} | Source: {data.get('source') if data else 'N/A'}")

        if not data.get("found"):
            # Try once without cache
            print("Attempt 2 (FORCE REFRESH):")
            data = await lyrics_service.get_lyrics(artist, title, use_cache=False)
            print(f"Found: {data.get('found')} | Source: {data.get('source') if data else 'N/A'}")

    except Exception as e:
        print(f"Error: {e}")


async def main():
    songs = [
        ("Michael Jackson", "Billie Jean"),
        ("Queen", "Bohemian Rhapsody"),
        ("The Weeknd", "Blinding Lights"),
    ]
    for artist, title in songs:
        await test_song(artist, title)


if __name__ == "__main__":
    asyncio.run(main())
