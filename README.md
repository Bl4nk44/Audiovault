# SpotizerrNew

SpotizerrNew to nowoczesna aplikacja webowa umożliwiająca pobieranie, zarządzanie i odtwarzanie muzyki z różnych źródeł (Spotify, YouTube).

## Główne Funkcjonalności

*   **Pobieranie Muzyki:** Pobieranie utworów, albumów i playlist ze Spotify oraz YouTube.
*   **Biblioteka:** Zarządzanie pobranymi utworami z możliwością wyszukiwania i filtrowania.
*   **Odtwarzacz:** Wbudowany odtwarzacz audio z wizualizacją i obsługą playlist.
*   **Watchlist:** Automatyczne monitorowanie i pobieranie nowych utworów od ulubionych artystów.
*   **Streaming:** Możliwość streamowania utworów przed pobraniem.

## Technologie

*   **Backend:** Python, FastAPI, SQLAlchemy, yt-dlp
*   **Frontend:** React, TypeScript, TailwindCSS, Zustand
*   **Baza Danych:** SQLite (Dev) / PostgreSQL (Prod)
*   **Cache:** Redis (opcjonalnie)

## Instalacja i Uruchomienie

### Backend

1.  Przejdź do katalogu `backend`.
2.  Utwórz wirtualne środowisko: `python -m venv venv`.
3.  Aktywuj środowisko: `venv\Scripts\activate` (Windows) lub `source venv/bin/activate` (Linux).
4.  Zainstaluj zależności: `pip install -r requirements.txt`.
5.  Uruchom serwer: `uvicorn app.main:app --reload`.

### Frontend

1.  Przejdź do katalogu `frontend`.
2.  Zainstaluj zależności: `npm install`.
3.  Uruchom aplikację: `npm run dev`.

## Autor

Bl4nk44
