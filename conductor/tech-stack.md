# Tech Stack - Audiovault

## Core Languages
- **Python:** Główny język backendu, wybrany ze względu na bogaty ekosystem bibliotek do przetwarzania audio i integracji z zewnętrznymi serwisami.
- **TypeScript:** Język frontendu, zapewniający bezpieczeństwo typów i lepszą strukturę aplikacji React.

## Backend Frameworks & Libraries
- **FastAPI:** Nowoczesny, szybki framework webowy do budowy API, wykorzystujący typowanie Python i operacje asynchroniczne.
- **SQLAlchemy (Async):** Zaawansowany ORM do obsługi bazy danych w sposób nieblokujący.
- **yt-dlp:** Kluczowe narzędzie do pobierania i przetwarzania strumieni audio/wideo z setek platform.
- **APScheduler:** System harmonogramowania zadań w tle (np. Auto-Sync dla watchlist).
- **Redis:** Wykorzystywany do buforowania (caching) oraz jako broker wiadomości dla procesów w tle.

## Frontend Frameworks & Libraries
- **React:** Biblioteka do budowy interfejsu użytkownika, oferująca komponentowe podejście i szybkość działania.
- **TailwindCSS v4:** Najnowsza wersja frameworka CSS, zapewniająca wysoką wydajność stylowania i nowoczesne narzędzia projektowe.
- **Framer Motion:** Zaawansowana biblioteka do animacji, kluczowa dla estetyki "Liquid Neon".
- **i18next:** Zarządzanie tłumaczeniami interfejsu.

## Database & Storage
- **SQLite:** Domyślna, lekka baza danych dla instalacji domowych.
- **PostgreSQL:** Wspierana opcja dla zaawansowanych użytkowników i większych bibliotek.
- **Lokalny System Plików:** Zarządzanie pobranymi plikami audio w ustrukturyzowanej hierarchii.

## Infrastructure
- **Docker & Docker Compose:** Standard konteneryzacji, umożliwiający łatwe uruchomienie aplikacji w dowolnym środowisku.
- **WebSockets:** Komunikacja w czasie rzeczywistym między backendem a frontendem (np. postęp pobierania).
- **Subsonic API:** Implementacja standardu API v1.16.1 dla zewnętrznych klientów mobilnych.
