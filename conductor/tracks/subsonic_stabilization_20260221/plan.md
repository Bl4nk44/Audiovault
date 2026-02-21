# Implementation Plan: Subsonic Stabilization

## Phase 1: Analiza i przygotowanie (Analysis)
- [~] **Task: Analiza obecnego stanu testów i API**
    - [ ] Uruchomienie istniejących testów Subsonic i identyfikacja błędów
    - [ ] Przegląd niezatwierdzonych zmian w `backend/app/api/subsonic/`
    - [ ] Wygenerowanie raportu pokrycia dla modułu Subsonic
- [ ] **Task: Conductor - User Manual Verification 'Phase 1: Analiza' (Protocol in workflow.md)**

## Phase 2: Stabilizacja i Naprawy (Stabilization)
- [ ] **Task: Poprawa błędnych testów i handlerów**
    - [ ] Naprawa handlerów w `backend/app/api/subsonic/handlers/` na podstawie błędów z Fazy 1
    - [ ] Implementacja brakujących testów jednostkowych dla `auth.py` i `media.py`
    - [ ] Weryfikacja mechanizmu Legacy Auth
- [ ] **Task: Conductor - User Manual Verification 'Phase 2: Stabilizacja' (Protocol in workflow.md)**

## Phase 3: Finalna Weryfikacja i Pokrycie (Verification)
- [ ] **Task: Ostateczny boost pokrycia testami**
    - [ ] Dopisanie testów dla przypadków brzegowych w `browse.py` i `search.py`
    - [ ] Uruchomienie pełnego zestawu testów backendu
    - [ ] Potwierdzenie pokrycia >80% dla całego modułu Subsonic
- [ ] **Task: Conductor - User Manual Verification 'Phase 3: Finalizacja' (Protocol in workflow.md)**
