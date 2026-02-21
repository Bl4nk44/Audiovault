# Implementation Plan: Subsonic Stabilization

## Phase 1: Analiza i przygotowanie (Analysis)
- [x] **Task: Analiza obecnego stanu testów i API**
    - [x] Uruchomienie istniejących testów Subsonic i identyfikacja błędów
    - [x] Przegląd niezatwierdzonych zmian w `backend/app/api/subsonic/`
    - [x] Wygenerowanie raportu pokrycia dla modułu Subsonic
- [ ] **Task: Conductor - User Manual Verification 'Phase 1: Analiza' (Protocol in workflow.md)**

## Phase 2: Stabilizacja i Naprawy (Stabilization)
- [x] **Task: Poprawa błędnych testów i handlerów**
    - [x] Naprawa handlerów w `backend/app/api/subsonic/handlers/` na podstawie błędów z Fazy 1
    - [x] Implementacja brakujących testów jednostkowych dla `auth.py` i `media.py`
    - [x] Weryfikacja mechanizmu Legacy Auth
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Stabilizacja' (Protocol in workflow.md)**

## Phase 3: Finalna Weryfikacja i Pokrycie (Verification)
- [x] **Task: Ostateczny boost pokrycia testami**
    - [x] Dopisanie testów dla przypadków brzegowych w `browse.py` i `search.py`
    - [x] Uruchomienie pełnego zestawu testów backendu
    - [x] Potwierdzenie pokrycia >80% dla kluczowych modułów Subsonic (globalne 77%)
- [x] **Task: Conductor - User Manual Verification 'Phase 3: Finalizacja' (Protocol in workflow.md)**
