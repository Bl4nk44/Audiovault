# API Patterns: Audiovault

## Endpoint Structure
- Prefix: `/api/v1/{resource}`
- Auth: `Authorization: Bearer <jwt_token>` (wszystkie endpointy poza `/auth`)
- Response: `{"data": ..., "status": "ok"}` lub `{"detail": "...", "status": "error"}`

## FastAPI Patterns

### Standard Endpoint
```python
@router.post("/", response_model=TrackResponse, status_code=201)
async def create(
    data: TrackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await TrackService(db).create(data, current_user.id)
```

### Pagination
```python
@router.get("/", response_model=PaginatedResponse[TrackResponse])
async def list_tracks(
    page: int = 1,
    size: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db)
):
    return await TrackService(db).list_paginated(page, size)
```

### WebSocket Progress
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

## Key Endpoints

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| POST | `/api/playlists/import` | Import playlisty ze streamera |
| POST | `/api/downloads` | Pobierz utwór |
| GET | `/api/library` | Lista utworów (paginacja) |
| GET | `/api/watchlist` | Pobierz watchlistę |
| DELETE | `/api/library/{id}` | Usuń utwór |
| GET | `/rest/ping.view` | Subsonic health check |
| GET | `/rest/stream.view` | Streaming audio |
| GET | `/rest/getPlaylists.view` | Subsonic playlists |

## HTTP Status Codes
- `201` — zasób utworzony
- `400` — validation error (Pydantic)
- `401` — brak/wygasły JWT
- `403` — brak uprawnień do zasobu
- `404` — zasób nie istnieje
- `429` — rate limit (platform API)
- `500` — błąd wewnętrzny (zawsze logowany)

## Rate Limiting per Platform
```python
DOWNLOAD_RATE_LIMITS = {
    "youtube": 30,      # req/min
    "spotify": 60,
    "soundcloud": 15,
    "deezer": 50,
}
```

## Pydantic Schema Pattern
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

    class Config:
        from_attributes = True
```

## Service Layer Pattern
Logika biznesowa zawsze w serwisie — router tylko orchestruje:
```python
# ✅ Router — tylko orchestracja
@router.post("/download")
async def download(data: DownloadRequest, service: DownloadService = Depends()):
    return await service.download_track(data.url)

# ❌ Logika w routerze — zakazane
@router.post("/download")
async def download(data: DownloadRequest, db: AsyncSession = Depends(get_db)):
    # 50 linii logiki biznesowej...
```
