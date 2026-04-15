# Audiovault — Wzorce Kodu

Czytaj ten plik gdy piszesz kod. Wzorce są wymagane — nie opcjonalne.

## 1. Service Layer — wymagane

```python
# ✅ Route tylko orchestruje
@router.post("/playlists/import")
async def import_playlist(url: str, db: AsyncSession = Depends(get_db)):
    return await PlaylistService(db).import_playlist(url)

# ❌ Logika w routerze
@router.post("/playlists/import")
async def import_playlist(url: str, db: AsyncSession = Depends(get_db)):
    # 50 linii logiki biznesowej...
```

## 2. Async DB Queries — wymagane

```python
# ✅
async def get_playlist(db: AsyncSession, playlist_id: int) -> Playlist | None:
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    return result.scalar_one_or_none()

# ❌ Blokujący ORM
def get_playlist(db: Session, playlist_id: int):
    return db.query(Playlist).filter(...).first()
```

## 3. Avoid N+1 Queries — użyj selectinload

```python
# ✅ Jedna zapytanie z eager loading
playlists = await db.execute(
    select(Playlist).options(selectinload(Playlist.tracks))
)

# ❌ Osobne zapytanie per wiersz
for playlist in playlists.scalars():
    print(playlist.tracks)  # N+1
```

## 4. Blocking yt-dlp in Async Context — wymagane

```python
# ✅ Wrap w thread
async def download_track(url: str, output_path: str) -> dict:
    ydl_opts = {"format": "bestaudio", "outtmpl": output_path}
    return await asyncio.to_thread(_sync_download, url, ydl_opts)

def _sync_download(url: str, opts: dict) -> dict:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)

# ❌ Blokuje event loop
with yt_dlp.YoutubeDL(opts) as ydl:
    ydl.download([url])
```

## 5. Concurrent Platform Queries — asyncio.gather

```python
# ✅
async def search_all_platforms(query: str) -> list[SearchResult]:
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            search_spotify(session, query),
            search_youtube(session, query),
            search_soundcloud(session, query),
            return_exceptions=True,
        )
    return [r for r in results if not isinstance(r, Exception)]
```

## 6. TanStack Query dla Server State

```typescript
// ✅
const { data, isLoading } = useQuery({
  queryKey: ['tracks'],
  queryFn: trackApi.getAll
});
const mutation = useMutation({
  mutationFn: downloadTrack,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tracks'] }),
});

// ❌ Manualny state dla danych serwera
const [tracks, setTracks] = useState([]);
useEffect(() => { fetch('/api/tracks').then(setTracks); }, []);
```

## 7. Zustand dla Client State

```typescript
// ✅ Theme/auth/UI state
const useThemeStore = create<ThemeStore>((set) => ({
  theme: 'dark',
  setTheme: (theme) => set({ theme }),
}));

// ❌ Context API dla globalnego stanu
const ThemeContext = createContext(...);
```

## 8. Socket.IO — Progress Updates

```python
# Backend
await sio.emit('download_progress', {
    'playlist_id': playlist_id,
    'progress': percent,
    'status': 'downloading',
})
```

```typescript
// Frontend
const socket = io('http://localhost:8000');
socket.on('download_progress', ({ playlist_id, progress }) => {
  updateProgress(playlist_id, progress);
});
```

## 9. Pydantic v2 Schema Pattern

```python
class TrackBase(BaseModel):
    title: str
    artist: str

class TrackCreate(TrackBase):
    url: str

class TrackResponse(TrackBase):
    id: int
    file_path: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)  # v2, nie class Config
```

## 10. Custom Exceptions

```python
class AudiovaultException(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code

class PlaylistNotFoundError(AudiovaultException):
    def __init__(self, playlist_id: int):
        super().__init__(
            f"Playlist {playlist_id} not found",
            "PLAYLIST_NOT_FOUND",
            404
        )
```
