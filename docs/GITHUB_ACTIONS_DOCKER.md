# 🤖 GitHub Actions - Auto Docker Build

## Co To Robi?

Każdy raz kiedy:
1. ✅ Push'ujesz do `main` → Automatycznie buduje Docker image
2. ✅ Tworzysz tag (np. `v1.0.0`) → Automatycznie buduje i pushuje
3. ✅ Pull Request na `main` → Testuje build (bez push'a)

---

## 🔑 KROK 1: Dodaj Sekrety do GitHub

Muszą być dodane sekrety do repo!

### Jak Dodać?

1. Przejdź do: **https://github.com/Bl4nk44/Audiovault/settings/secrets/actions**
2. Kliknij **"New repository secret"**

### Dodaj Te Sekrety:

#### Secret 1: DOCKER_USERNAME
```
Name: DOCKER_USERNAME
Value: bl4nk404
```
Kliknij "Add secret"

#### Secret 2: DOCKER_PASSWORD
```
Name: DOCKER_PASSWORD
Value: [Twoje hasło do Docker Hub ALBO Token]
```
Kliknij "Add secret"

---

### 💡 Porada: Użyj Docker Hub Access Token (Bardziej Bezpieczne!)

1. Zaloguj się: https://hub.docker.com/
2. Kliknij profil → Settings → Security
3. Kliknij "New Access Token"
4. Nazwa: `github-actions`
5. Uprawnienia: Read & Write
6. Skopiuj token
7. Wklej do GitHub Secret jako DOCKER_PASSWORD

---

## ✅ KROK 2: Testuj Actions

GitHub Actions będzie automatycznie działać.

### Sprawdzenie

1. Przejdź do: **https://github.com/Bl4nk44/Audiovault/actions**
2. Powinieneś widzieć workflow'i

---

## 🚀 Jak Używać?

### Opcja 1: Auto-Build przy Push'u na Main

```bash
# Push zmian
git add .
git commit -m "feat: Add feature"
git push origin main

# GitHub Actions automatycznie zrobią:
# 1. Zbuduje Docker image
# 2. Pushnie na Docker Hub jako: bl4nk404/audiovault:latest
# 3. Zaktualizuje Docker Hub description
```

### Opcja 2: Build Specificzną Wersję (POLECANE!)

```bash
# Stwórz tag
git tag v1.0.1
git push origin v1.0.1

# GitHub Actions automatycznie zrobią:
# 1. Zbuduje Docker image
# 2. Pushnie na Docker Hub jako:
#    - bl4nk404/audiovault:1.0.1
#    - bl4nk404/audiovault:1.0
#    - bl4nk404/audiovault:latest
```

---

## 📊 Co Się Dzieje w GitHub Actions?

### Workflow Kroki:

1. **Checkout code** - Ściąga kod z repo
2. **Set up Docker Buildx** - Przygotowuje builder
3. **Login to Docker Hub** - Loguje się (używa DOCKER_USERNAME i DOCKER_PASSWORD)
4. **Extract metadata** - Wyciąga tagi (latest, v1.0.0, SHA, etc.)
5. **Build and push** - Buduje i pushuje image
6. **Update Docker Hub Description** - Aktualizuje opis na Docker Hub

---

## 🏷️ Jak Działają Tagi

### Jeśli Push'ujesz do Main
```
bl4nk404/audiovault:latest ← Zawsze latest
bl4nk404/audiovault:main ← Branch name
bl4nk404/audiovault:abc123def ← Short SHA
```

### Jeśli Tworzysz Tag v1.0.1
```
bl4nk404/audiovault:1.0.1 ← Full version
bl4nk404/audiovault:1.0 ← Major.Minor
bl4nk404/audiovault:latest ← Latest
bl4nk404/audiovault:abc123def ← Short SHA
```

---

## 🔍 Monitoring Actions

### 1. Przejdź do Actions
https://github.com/Bl4nk44/Audiovault/actions

### 2. Kliknij Workflow
Widzisz listę run'ów

### 3. Kliknij Run
Widzisz szczegóły buildu

### 4. Expanduj Kroki
Widzisz każdy krok (Build, Push, etc.)

---

## ✨ Przykład - Całe Wersjonowanie

```bash
# 1. Zrób zmiany
echo "v1.0.1" > VERSION.txt

# 2. Commitnij
git add .
git commit -m "Release v1.0.1"
git push origin main
# GitHub Actions buduje i pushuje: latest, main, sha

# 3. Stwórz tag (release)
git tag v1.0.1
git push origin v1.0.1
# GitHub Actions buduje i pushuje: 1.0.1, 1.0, latest, sha

# 4. Sprawdź Docker Hub
# https://hub.docker.com/r/bl4nk404/audiovault/tags
# Powinieneś widzieć: latest, 1.0.1, 1.0, main, sha, etc.
```

---

## ⚙️ Konfiguracja Workflow

### Kiedy Trigger'uje?

```yaml
on:
  push:
    branches:
      - main           # Każdy push na main
    tags:
      - 'v*'          # Każdy tag zaczynający się od 'v'
  pull_request:
    branches:
      - main          # Pull request na main (test, bez push'a)
```

### Push Happens When:
```yaml
push: ${{ github.event_name != 'pull_request' }}
# = Pushuje gdy: push na main lub tag
# = NIE pushuje: Pull request
```

---

## 🆘 Troubleshooting

### "Workflow file not found"
```
Problem: Workflow się nie uruchamia
Rozwiązanie: Sprawdź czy plik jest w .github/workflows/docker-build.yml
```

### "Authentication failed"
```
Problem: GitHub Actions nie może zalogować do Docker Hub
Rozwiązanie:
  1. Przejdź do Settings → Secrets
  2. Sprawdź DOCKER_USERNAME i DOCKER_PASSWORD
  3. Upewnij się że hasło to token (nie hasło)
  4. Token powinien mieć uprawnienia Read & Write
```

### Workflow się nie uruchamia

```
Problem: Push'uję ale Actions się nie uruchamia
Rozwiązanie:
  1. Sprawdzam czy sekrety są w Settings → Secrets
  2. Sprawdzam czy workflow file istnieje: .github/workflows/docker-build.yml
  3. Czekam kilka sekund
  4. Refreshuję stronę Actions
```

---

## 📚 Linki

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Build Action](https://github.com/docker/build-push-action)
- [Docker Metadata Action](https://github.com/docker/metadata-action)
- [Semantic Versioning](https://semver.org/)
- [Docker Hub Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)

---

## ✅ Checklist

- [ ] Przejść do Settings → Secrets
- [ ] Dodać DOCKER_USERNAME = bl4nk404
- [ ] Dodać DOCKER_PASSWORD = token/password
- [ ] Push'nąć do main: `git push origin main`
- [ ] Sprawdzić Actions: https://github.com/Bl4nk44/Audiovault/actions
- [ ] Czekać 5-10 minut
- [ ] Sprawdzić Docker Hub: nowe image powinno być
- [ ] Utworzyć tag i testować: `git tag v1.0.1; git push origin v1.0.1`

---

## 🎉 Done!

Od teraz, każdy raz kiedy push'ujesz lub tworzysz tag:
1. ✅ GitHub Actions automatycznie buduje Docker image
2. ✅ Pushuje na Docker Hub
3. ✅ Badge w README pokazuje pobrania
4. ✅ Wszystko jest zautomatyzowane!

---

**Potrzebujesz pomocy?** Sprawdź GitHub Actions logs! 🚀
