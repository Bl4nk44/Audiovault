# Workflow: Code Review

## Kiedy używać
Przed merge PR, code improvements, pair programming.

## Checklist — Backend (Python)

- [ ] Async/await wszędzie (brak blocking calls w async context)
- [ ] Type hints na wszystkich sygnaturach
- [ ] Docstrings dla publicznych metod (Google style)
- [ ] Logika w service layer, **nie** w routerach
- [ ] `selectinload()` dla relacji (brak N+1 queries)
- [ ] Custom exceptions zamiast generycznych
- [ ] Właściwe HTTP status codes (201 dla create, 204 dla delete)
- [ ] Migracja Alembic przy każdej zmianie modelu DB
- [ ] Testy: happy path + edge cases + sad path

## Checklist — Frontend (TypeScript)

- [ ] Brak `any` — wszystkie typy zdefiniowane
- [ ] React Query dla server state (nie ręczny fetch w `useEffect`)
- [ ] `queryClient.invalidateQueries` po każdej mutacji
- [ ] TailwindCSS (brak inline styles)
- [ ] `memo` / `useMemo` dla kosztownych komponentów
- [ ] Named exports
- [ ] Error boundaries dla poddrzew komponentów

## Checklist — Ogólny

- [ ] SRP — każda klasa/funkcja robi jedną rzecz
- [ ] DRY — brak powtórzeń
- [ ] Brak sekretów w kodzie (env vars)
- [ ] Brak `console.log` debug
- [ ] CI zielone (testy przechodzą)
- [ ] CHANGELOG zaktualizowany
- [ ] Breaking changes opisane w PR

## Proces

1. **Scan** — przeczytaj opis PR, sprawdź zakres zmian, red flags
2. **Review** — plik po pliku wg checklistry, test lokalnie jeśli potrzeba
3. **Feedback** — konstruktywnie:
   ```
   ❌ N+1 query w `get_playlists_with_tracks()` (linia 45)
   ✅ Użyj selectinload(Playlist.tracks)
   ```
4. **Decyzja:**
   - **Approve** — critical issues resolved, CI green, wzorce zachowane
   - **Request Changes** — bugi, security issues, broken tests, major arch concerns

## Must-Have przed Approve
1. CI green
2. Brak `console.log`/debug code
3. Type hints/types
4. Error handling
5. Dokumentacja zaktualizowana
6. Brak oczywistych security issues
7. Wzorce zachowane
8. CHANGELOG entry
