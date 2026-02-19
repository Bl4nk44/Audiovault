# Workflow: Feature Development

## Kiedy używać
Nowa integracja platformy, nowy endpoint, komponenty UI, rozszerzenie funkcji.

## Proces

### 1. Planning (przed kodowaniem)
1. Wczytaj `.agent/memory-bank/` — sprawdź podobne implementacje
2. Zidentyfikuj dotknięte komponenty: backend, modele DB + migracje, frontend, testy
3. Oceń breaking changes i ryzyka
4. **Przedstaw plan i czekaj na potwierdzenie**

### 2. Backend — kolejność implementacji
1. `app/schemas/` — Pydantic schema (walidacja in/out)
2. `app/models/` — SQLAlchemy model + migracja Alembic
3. `app/services/` — cała logika biznesowa
4. `app/api/routes/` — tylko orchestracja, bez logiki
5. Rejestracja routera w `app/api/api.py`
6. Testy w `backend/tests/` (min. 80% coverage)

### 3. Nowa platforma streamingowa
1. `app/services/extractors/<platform>_service.py` z metodami `parse_url()`, `fetch_playlist()`, `search_track()`
2. Rejestracja w `app/services/platform_registry.py`
3. Frontend: komponenty w `frontend/src/components/platforms/`
4. Logo + styling + i18n klucze

### 4. Frontend — kolejność implementacji
1. `src/types/` — interfejsy TypeScript
2. `src/services/api/` — API client
3. `src/hooks/use<Feature>.ts` — custom hook
4. `src/components/<Feature>/` — komponenty
5. `src/pages/` — integracja w stronie
6. Testy (Vitest + RTL)

### 5. Wymagania testów
- Backend: pytest-asyncio, fixtures w `conftest.py`, happy path + edge cases
- Frontend: testuj interakcje użytkownika, nie implementację
- Zawsze: null/empty/error states przetestowane

### 6. Commit & PR
```
feat(scope): Krótki opis funkcji

- Co dodano
- Kluczowe decyzje
- Breaking changes (jeśli są)

Closes #nr
```

## Pułapki
- Brak `await` na DB operations → zwraca coroutine
- N+1 queries → `selectinload()`
- Logika biznesowa w routerze
- Hardcoded wartości zamiast env vars
- Breaking API bez wersjonowania
- Brak migracji przy zmianie modelu

## Checklist
- [ ] Plan zatwierdzony przed kodowaniem
- [ ] Backend tests ≥ 80% coverage
- [ ] Frontend tests napisane
- [ ] Migracja DB stworzona
- [ ] CHANGELOG zaktualizowany
- [ ] README zaktualizowany (jeśli user-facing)
- [ ] Brak breaking changes bez ostrzeżenia
