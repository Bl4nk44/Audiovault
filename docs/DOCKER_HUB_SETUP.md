# 🐳 Docker Hub Setup - Kompletny Poradnik

## Cel
Umieścić obraz Audiovault na Docker Hub i podpiąć badge z liczbą pobrań do README.

---

## KROK 1: Stwórz Konto Docker Hub

### Jeśli Jeszcze Go Nie Masz

1. Przejdź do: https://hub.docker.com/
2. Kliknij **"Sign Up"** (prawy górny róg)
3. Zarejestruj się:
   - Username: `bl4nk44` (taki sam jak GitHub)
   - Email: `bl4nk44@pm.me`
   - Password: Silne hasło
4. Potwierdź email (będzie link w wiadomości)
5. Zaloguj się na konto

---

## KROK 2: Utwórz Repository na Docker Hub

1. Zalogowany, kliknij profil (prawy górny róg) → **"Repositories"**
2. Kliknij **"Create a Repository"** (przycisku)
3. Wypełnij formularz:
   ```
   Repository name: audiovault
   Description: Your Personal Music Sanctuary - Self-hosted music downloader
   Visibility: Public (ważne! Aby inni mogli ściągać)
   ```
4. Kliknij **"Create"**

**Będziesz mieć:** https://hub.docker.com/r/bl4nk44/audiovault

---

## KROK 3: Przygotuj Dockerfile

Musisz mieć plik `Dockerfile` w głównym katalogu repozytorium.

### Jeśli Masz Backend i Frontend Osobno

**`Dockerfile.backend`**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`Dockerfile.frontend`**:
```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Runtime stage
FROM node:18-alpine

WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
```

### Multi-Stage Build (Backend + Frontend Razem)

**`Dockerfile`** (główny katalog):
```dockerfile
# Backend builder
FROM python:3.11-slim as backend-builder

WORKDIR /backend
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend builder
FROM node:18-alpine as frontend-builder

WORKDIR /frontend
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Final stage
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY --from=backend-builder /backend .

# Copy frontend built files
COPY --from=frontend-builder /frontend/dist ./static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## KROK 4: Zaloguj Się Lokalnie do Docker

### Na Komputerze

```bash
# Zaloguj się
docker login

# Będziesz poproszony o:
# Username: bl4nk44
# Password: Hasło Docker Hub (które ustawiłeś)

# Sprawdzenie
docker login -u bl4nk44
```

---

## KROK 5: Build Obrazu

### Opcja A: Build Konkretnego Komponentu

```bash
# Dla backend
docker build -f Dockerfile.backend -t bl4nk44/audiovault:backend-latest .
docker build -f Dockerfile.backend -t bl4nk44/audiovault:backend-1.0.0 .

# Dla frontend
docker build -f Dockerfile.frontend -t bl4nk44/audiovault:frontend-latest .
docker build -f Dockerfile.frontend -t bl4nk44/audiovault:frontend-1.0.0 .
```

### Opcja B: Build Multi-Stage (Cały Projekt)

```bash
# Build główny image
docker build -t bl4nk44/audiovault:latest .

# Lub z wersją
docker build -t bl4nk44/audiovault:1.0.0 .
docker build -t bl4nk44/audiovault:latest .
```

### Opcja C: Tag Oddzielnie (Jeśli Masz Już Obraz)

```bash
# Jeśli już masz obraz:
docker tag audiovault:latest bl4nk44/audiovault:latest
docker tag audiovault:1.0.0 bl4nk44/audiovault:1.0.0
```

---

## KROK 6: Push na Docker Hub

### Push Pojedynczego Obrazu

```bash
# Push latest
docker push bl4nk44/audiovault:latest

# To potrwa kilka minut, czekaj aż się skończy
```

### Push Wielu Tagów

```bash
# Push wersji
docker push bl4nk44/audiovault:1.0.0
docker push bl4nk44/audiovault:1.0.1
docker push bl4nk44/audiovault:latest

# Lub jeśli masz backend/frontend
docker push bl4nk44/audiovault:backend-latest
docker push bl4nk44/audiovault:frontend-latest
```

### Sprawdzenie Postępu

```bash
# Sprawdź czy image jest na Docker Hub
docker images | grep bl4nk44/audiovault

# Lub odwiedzić:
# https://hub.docker.com/r/bl4nk44/audiovault
```

---

## KROK 7: Badge w README (już umieszczone!)

### Badge Jest Już w README

```markdown
[![Docker Pulls](https://img.shields.io/docker/pulls/bl4nk44/audiovault?logo=docker)](https://hub.docker.com/r/bl4nk44/audiovault)
```

To pokazuje:
- ✅ Ikonę Docker
- ✅ Liczbę pobrań
- ✅ Link do Docker Hub

### Jak To Wygląda

```
[Docker Icon] 42 pulls → link do https://hub.docker.com/r/bl4nk44/audiovault
```

---

## KROK 8: Automatyczne Buildy (GitHub Actions)

Możesz ustawić automatyczne buildy, gdy pushasz do GitHub.

### Stwórz `.github/workflows/docker-build.yml`

```yaml
name: Build Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: |
            bl4nk44/audiovault:latest
            bl4nk44/audiovault:${{ github.sha }}
          labels: |
            org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
            org.opencontainers.image.revision=${{ github.sha }}
```

### Dodaj Sekrety

1. Przejdź do: https://github.com/Bl4nk44/Audiovault/settings/secrets/actions
2. Kliknij **"New repository secret"**
3. Dodaj:
   - **Name**: `DOCKER_USERNAME`
   - **Value**: `bl4nk44`
4. Kliknij **"Add secret"**
5. Powtórz dla hasła:
   - **Name**: `DOCKER_PASSWORD`
   - **Value**: Twoje hasło Docker Hub

---

## Troubleshooting

### "repo not found" Badge

```
❌ Problem: Badge pokazuje "repo not found"
✅ Rozwiązanie: Musisz pushną obraz! (KROK 6)
```

### "Unauthorized" przy docker push

```bash
# Problem: Nie jesteś zalogowany
# Rozwiązanie:
docker login  # Zaloguj się
docker push bl4nk44/audiovault:latest  # Retry
```

### Obraz Jest Za Duży

```bash
# Problem: Zbyt duży obraz
# Rozwiązania:

# 1. Użyj alpine/slim image
FROM python:3.11-slim  # 150MB zamiast 1GB

# 2. Multi-stage build
FROM python:3.11 as builder
# ... build ...
FROM python:3.11-slim
COPY --from=builder ...

# 3. Usuń niepotrzebne pliki
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
```

### Docker Hub Mówi "Limit"

```
Docker Hub ma limit pobrań dla bezpłatnych kont:
- 6 godzin: 200 pobrań
- 24 godziny: 2000 pobrań

Uzasadnienie: Bezpłatne konto
Rozwiązanie: Rozważ GitHub Packages lub upgrade konta
```

---

## Checklist Kompletny

- [ ] Stworzyłem konto Docker Hub (`bl4nk44`)
- [ ] Stworzyłem repository `audiovault` (Public)
- [ ] Mam `Dockerfile` lub `Dockerfile.backend`/`Dockerfile.frontend`
- [ ] Zalogowałem się: `docker login`
- [ ] Zbuildowałem obraz: `docker build -t bl4nk44/audiovault:latest .`
- [ ] Pushowałem obraz: `docker push bl4nk44/audiovault:latest`
- [ ] Badge w README pokazuje liczby: `repo not found` → liczba
- [ ] Testowałem: `docker pull bl4nk44/audiovault:latest`

---

## Komendy Szybkie Referencje

```bash
# Login
docker login

# Build
docker build -t bl4nk44/audiovault:latest .

# Push
docker push bl4nk44/audiovault:latest

# Pull (test)
docker pull bl4nk44/audiovault:latest

# Run (test)
docker run -p 8000:8000 bl4nk44/audiovault:latest

# List
docker images | grep audiovault

# Remove
docker rmi bl4nk44/audiovault:latest
```

---

## Następne Kroki

1. ✅ Build i push obrazu
2. ✅ Verify na Docker Hub
3. ✅ Test: `docker pull bl4nk44/audiovault:latest`
4. ✅ Badge w README pokaże liczby
5. ⏭️ Setup GitHub Actions (automatyczne buildy)
6. ⏭️ Dodaj więcej tagów (latest, v1.0.0, etc.)

---

## Linki Pomocne

- [Docker Hub](https://hub.docker.com/)
- [Docker Build Docs](https://docs.docker.com/engine/reference/commandline/build/)
- [Docker Push Docs](https://docs.docker.com/engine/reference/commandline/push/)
- [Shields.io Badge Generator](https://shields.io/)
- [GitHub Actions Docker](https://github.com/docker/build-push-action)

---

**Gotowe?** Zacznij od KROKU 1 i idź krok po kroku. Pisz jeśli masz problemy! 🚀
