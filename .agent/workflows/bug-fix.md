# Workflow: Bug Fix

## Kiedy używać
Zgłoszenie błędu, testy nie przechodzą, alerty monitoringu, code review znalazł problem.

## Proces

### 1. Reprodukcja
- Zebrać: logi, środowisko, kroki do odtworzenia, oczekiwane vs aktualne zachowanie
- Stworzyć minimalną reprodukcję w dev
- Sprawdzić czy to regresja (działało wcześniej?)

```bash
docker compose logs backend | grep ERROR
docker compose logs frontend --tail=50
curl -X POST http://localhost:8000/api/download -H "Content-Type: application/json" -d '{"url":"..."}'
sqlite3 backend/audiovault.db "SELECT * FROM tracks WHERE id = ?;"
```

### 2. Diagnoza — kategorie błędów
- **Download** — yt-dlp outdated, geo-restriction, invalid URL, timeout
- **Database** — missing migration, constraint violation, N+1, SQLite lock
- **Auth** — JWT expired, CORS, missing header
- **UI** — state nie aktualizuje, WebSocket disconnect, race condition

### 3. Fix
- Implementuj w odpowiedniej warstwie (service, nie route)
- **Napisz test regresji PRZED commitem**
- Zaktualizuj `.agent/memory-bank/patterns/common-issues.md` jeśli to częsty błąd

### 4. Dokumentacja
```bash
# CHANGELOG.md
### Fixed
- Opis naprawy (#numer_issue)
```

```
fix(scope): Krótki opis naprawy

- Przyczyna
- Rozwiązanie
- Test regresji dodany

Fixes #nr
```

## Severity

| Poziom | Czas | Przykład |
|--------|------|----------|
| Critical | Natychmiast | Utrata danych, auth broken, serwis down |
| High | 24-48h | Core feature broken, znaczący user impact |
| Medium | Sprint | Workaround dostępny, edge case |
| Low | Backlog | Kosmetyka, rzadkie |

## Checklist
- [ ] Bug odtworzony konsekwentnie
- [ ] Root cause zidentyfikowany
- [ ] Fix zaimplementowany
- [ ] Test regresji dodany
- [ ] Manual testing OK
- [ ] Brak efektów ubocznych
- [ ] CHANGELOG zaktualizowany
