# Audiovault — Pułapki i Zależności

## Częste Błędy

### 1. Brak `await` na async DB calls
```python
# ❌ Zwraca coroutine, nie wynik
result = db.execute(select(Track))

# ✅
result = await db.execute(select(Track))
```

### 2. N+1 queries
```python
# ❌
for playlist in playlists:
    print(playlist.tracks)  # osobne zapytanie per playlist

# ✅ — użyj selectinload() w zapytaniu
```

### 3. Logika biznesowa w routerze
Routes = orchestracja. Logika → `services/`. Zawsze.

### 4. Hardcoded secrets
Zawsze przez env vars / `.env`. Nigdy w kodzie.

### 5. Brak migracji Alembic po zmianie modelu
Po każdej zmianie `models/`:
```bash
alembic revision --autogenerate -m "opis" && alembic upgrade head
```

### 6. `any` w TypeScript
```typescript
// ❌
const data: any = response.data;

// ✅
const data: unknown = response.data;
// lub zdefiniuj właściwy typ
```

### 7. Brak `queryClient.invalidateQueries` po mutacji
```typescript
// ❌ — UI pokazuje stare dane
mutation.mutate(data);

// ✅
onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tracks'] })
```

### 8. yt-dlp bezpośrednio w async context
Blokuje event loop. Zawsze `asyncio.to_thread()`. Patrz: `patterns.md#4`.

### 9. `requests` zamiast `aiohttp` w backendzie
`requests` jest blokujący. Używaj `aiohttp` (lub `httpx` async).

### 10. Pydantic v1 `class Config`
```python
# ❌ v1 — nie używaj
class Config:
    orm_mode = True

# ✅ v2
model_config = ConfigDict(from_attributes=True)
```

### 11. Brak obsługi wyjątków z `asyncio.gather`
```python
# ✅ — zawsze return_exceptions=True
results = await asyncio.gather(*tasks, return_exceptions=True)
successes = [r for r in results if not isinstance(r, Exception)]
```

### 12. TailwindCSS v4 — stare utility names
TailwindCSS v4 zmienił część nazw klas. Sprawdź changelog v4 przed użyciem nieznanych klas.

---

## Zależności do Obserwowania

| Pakiet | Ryzyko | Akcja |
|--------|--------|-------|
| **yt-dlp** | Breaking extractor changes — często | `uv add yt-dlp --upgrade` regularnie |
| **TailwindCSS v4** | Wciąż beta/alpha — API niestabilne | Sprawdź changelog przed upgrade |
| **SQLAlchemy 2.x** | Async patterns — unikaj v1 legacy syntax | Zawsze używaj `await db.execute()` |
| **React 19** | Concurrent features — nowe patterny | Sprawdź React docs dla nowych API |
| **FastAPI** | Drobne zmiany w Depends/lifespan | context7 przed upgrade |
