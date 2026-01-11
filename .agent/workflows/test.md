---
description: Uruchamianie testów backend przed pushem
---

# Uruchamianie Testów Backend

## W kontenerze Docker (zalecane)
// turbo
```bash
docker compose exec backend python -m pytest tests/ -v --tb=short
```

## Lokalne (jeśli masz Python zainstalowany)
```bash
cd backend
python -m pytest tests/ -v --tb=short
```

## Tylko konkretny moduł
// turbo
```bash
docker compose exec backend python -m pytest tests/api/subsonic/ -v
```

## Z generowaniem raportu pokrycia
```bash
docker compose exec backend python -m pytest tests/ -v --cov=app --cov-report=html
```

## Szybki test przed pushem (script)
// turbo
```bash
docker compose exec backend python tests/run_all.py
```
