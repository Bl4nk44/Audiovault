# Product Guidelines - Audiovault

## Prose Style
Dokumentacja i komunikaty wewnątrz aplikacji powinny być **techniczne, bezpośrednie i zwięzłe**. Skupiamy się na dostarczaniu wartości merytorycznej bez zbędnych ozdobników. Instrukcje powinny być łatwe do śledzenia, a błędy precyzyjnie opisane technicznie, by ułatwić debugowanie przez zaawansowanych użytkowników.

## Language Strategy
- **Kod i Dokumentacja Techniczna:** Wszystkie nazwy zmiennych, komentarze w kodzie oraz dokumentacja wewnątrz projektu (np. `docs/`, `CONTRIBUTING.md`) są prowadzone w języku **angielskim**, aby zapewnić spójność z ekosystemem open-source i bibliotekami.
- **Interfejs Użytkownika (UI):** Aplikacja korzysta z mechanizmu i18n, aby wspierać wiele języków, w tym polski, angielski, niemiecki i inne. Domyślnym językiem interfejsu jest angielski.

## Branding & Aesthetics
Aplikacja Audiovault bazuje na estetyce **"Liquid Neon"** oraz **"Audio-Centric Design"**:
- **Neonowy Modernizm:** Wykorzystanie głębokich czerni (Void) skontrastowanych z neonowymi akcentami (glowing borders) i efektami szklistości (glassmorphism).
- **Dynamika Audio:** Każdy element interfejsu powinien nawiązywać do świata dźwięku – od visualizerów w czasie rzeczywistym po płynne animacje przejść między stanami odtwarzania, budując dynamiczne doświadczenie dla użytkownika.

## User Experience (UX) Principles
- **Przejrzysty Feedback:** Użytkownik musi zawsze wiedzieć, co dzieje się w systemie. Każda akcja (pobieranie, dodawanie do kolejki, synchronizacja) musi być potwierdzona wizualnie, a w przypadku błędów system musi zwrócić czytelny komunikat o przyczynie awarii.
- **Płynność Interakcji:** Wykorzystanie technologii WebSocket do dostarczania powiadomień w czasie rzeczywistym o postępie procesów działających w tle (np. postęp pobierania przez yt-dlp).

## Design System Constraints
- **TailwindCSS v4:** Wszystkie style powinny być spójne z nowymi standardami TailwindCSS v4, unikając nadmiarowego CSS na rzecz utility-first.
- **Responsywność:** Design musi działać płynnie zarówno na dużych monitorach, jak i urządzeniach mobilnych, umożliwiając wygodne zarządzanie biblioteką z poziomu przeglądarki smartfona.
