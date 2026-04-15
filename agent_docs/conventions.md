# Audiovault — Konwencje Kodu

## Backend (Python)

**Ruff** — linter i formatter:
- `line-length = 120`
- `target-version = "py312"`
- Uruchom: `cd backend && ruff check --fix . && ruff format .`

**Pyright** (basic mode) + **mypy**:
- Uruchom: `cd backend && pyright app/`
- Type hints wymagane na wszystkich sygnaturach funkcji
- Nowoczesna składnia: `X | None`, `list[X]`, `dict[str, X]`
- Google-style docstrings dla publicznych API

**HTTP Status Codes:**
- `201` — create
- `204` — delete (no content)
- `400` — validation error
- `401` — unauthorized (brak/zły token)
- `403` — forbidden (brak uprawnień)
- `404` — not found
- `429` — rate limit

---

## Frontend (TypeScript)

**Prettier** (2-space indent) + **ESLint 10**:
- Uruchom: `cd frontend && npm run format && npm run lint`

**TypeScript 5.9 strict:**
- Uruchom: `cd frontend && npx tsc --noEmit`
- **Zakaz `any`** — używaj `unknown` zamiast
- `interface` dla obiektów, `type` dla union/aliasów
- Named exports domyślnie

**TailwindCSS v4:**
- Tylko klasy Tailwind — **zakaz inline styles**
- `tailwind-merge` + `clsx` dla warunkowych klas:

```typescript
import { cn } from '@/lib/utils';  // cn = twMerge(clsx(...))
className={cn('base-class', condition && 'conditional-class')}
```

---

## Glassmorphism Theme ("Liquid Neon")

```css
/* Tailwind equivalents */
backdrop-filter: blur(12px);              /* backdrop-blur-xl */
background: rgba(255,255,255,0.1);        /* bg-white/10 */
border: 1px solid rgba(255,255,255,0.2);  /* border border-white/20 */
```
- 6 color presets, dark mode default
- CSS variables w `:root`
- Nie łam motywu inline styles

---

## Security Toolchain

Profile skanów (VSCode Tasks):

| Profil | Narzędzia | Kiedy |
|--------|-----------|-------|
| `quick` | GitGuardian + Semgrep | Feature branch |
| `standard` | + OSV-Scanner + Checkov + Trivy FS + SonarQube | Pre-merge |
| `release` | + Trivy image scan | Pre-release |

```bash
ggshield secret scan path .                  # secrets
semgrep scan --config=auto backend/          # SAST
osv-scanner scan --recursive .              # vulnerable deps
```

---

## API Response Format

```python
# Sukces
{"data": ..., "status": "ok"}

# Błąd
{"detail": "...", "status": "error"}
```

Prefix: `/api/v1/{resource}`
Auth: `Authorization: Bearer <jwt>` (wszystkie endpointy poza `/auth`)
