# Track Specification: Subsonic Stabilization

## Overview
Celem tej ścieżki jest stabilizacja implementacji API Subsonic (v1.16.1) w Audiovault oraz zapewnienie wysokiej jakości testów automatycznych. Obecnie w projekcie znajduje się wiele niezatwierdzonych zmian w handlerach i testach Subsonic, które wymagają weryfikacji i finalizacji.

## Goals
- **Stabilność API:** Wszystkie endpointy Subsonic (auth, browse, media, search, lists, user, system) muszą działać zgodnie ze specyfikacją Subsonic.
- **Weryfikacja zmian:** Przegląd i zatwierdzenie modyfikacji w `backend/app/api/subsonic/`.
- **Pokrycie testami:** Zwiększenie pokrycia testami dla modułów Subsonic do poziomu >80%.
- **Kompatybilność:** Zapewnienie poprawnego działania z popularnymi klientami (Symfonium, Amperfy).

## Technical Requirements
- **Backend:** Python (FastAPI).
- **Testy:** Pytest, coverage reports.
- **API:** Subsonic v1.16.1 (Legacy Auth support).

## Out of Scope
- Dodawanie nowych platform streamingowych (np. Bandcamp).
- Refaktoryzacja frontendu niezwiązana z API Subsonic.
