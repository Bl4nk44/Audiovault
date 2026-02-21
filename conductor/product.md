# Initial Concept

Audiovault is a self-hosted application to import, manage, and download music libraries from streaming platforms.

# Product Guide - Audiovault

## Vision
Audiovault to potężna, samoobsługowa aplikacja zaprojektowana do importowania, zarządzania i pobierania bibliotek muzycznych z dowolnej większej platformy streamingowej bezpośrednio na lokalny serwer. Projekt łączy w sobie wysoką wydajność, nowoczesną estetykę "Liquid Neon" oraz niezawodność, dając użytkownikom pełną kontrolę nad ich kolekcją audio bez zależności od chmury.

## Target Audience
- **Self-hosters (NAS/HomeLab):** Osoby dbające o prywatność i posiadające własną infrastrukturę serwerową, które chcą hostować swoją muzykę samodzielnie.
- **Migranci Streamingowi:** Użytkownicy zmęczeni rosnącymi cenami i usuwaniem utworów z platform takich jak Spotify czy Tidal, szukający stabilnej alternatywy.

## Core Goals
1. **Automatyzacja Zarządzania Biblioteką:** Skupienie na mechanizmach watchlist, inteligentnej de-duplikacji oraz automatycznym pobieraniu nowych utworów z obserwowanych playlist.
2. **Niezawodność Ekosystemu Subsonic:** Zapewnienie bezbłędnej współpracy z najpopularniejszymi klientami mobilnymi (Symfonium, Amperfy, DSub), aby umożliwić streaming muzyki w dowolnym miejscu.
3. **Stabilność i Jakość Kodu (QA):** Rozbudowa zestawu testów automatycznych i stabilizacja procesu pobierania przez yt-dlp, aby minimalizować błędy przy dużych bibliotekach.

## Key Features
- **Uniwersalny Import:** Obsługa Spotify, YouTube, Deezer, SoundCloud, Apple Music, Tidal i Amazon Music.
- **Watchlisty & Auto-Sync:** Automatyczne sprawdzanie zmian w zdalnych bibliotekach i synchronizacja z lokalnym serwerem.
- **Streaming Subsonic:** Pełna implementacja API v1.16.1 dla odtwarzaczy mobilnych i desktopowych.
- **Wieloplatformowy Fallback:** Inteligentne wyszukiwanie alternatywnych źródeł w przypadku niedostępności utworu na pierwotnej platformie.
- **Nowoczesny UI:** Interfejs React z TailwindCSS v4, wspierający motywy neonowe i responsywne odtwarzanie.

## Constraints & Requirements
- **Infrastruktura:** System musi być lekki i działać stabilnie w kontenerach Docker.
- **Baza Danych:** Wsparcie dla SQLite (domyślnie dla łatwego startu) oraz PostgreSQL (dla większych instalacji).
- **Bezpieczeństwo:** Ochrona przed wyciekiem sekretów API i bezpieczne zarządzanie poświadceniami do platform zewnętrznych.
