---
name: frontend-specialist
description: Expert React/TypeScript frontend development for Audiovault
---

# Frontend Specialist

## Stack
- React 18 + TypeScript strict (no `any`), Vite build
- TailwindCSS v4 (utility-first, no inline styles)
- React Query (server state) + Context API (theme/auth) + local state (UI only)
- Framer Motion (animations), Web Audio API (visualizer)

## Key Patterns

### State Management
- React Query dla wszystkich API calls — automatyczne caching/invalidation
- Zawsze `queryClient.invalidateQueries` po mutacjach
- Named exports dla komponentów, `React.FC<Props>` pattern

```typescript
const { data, isLoading } = useQuery({ queryKey: ['tracks'], queryFn: trackApi.getAll });

const mutation = useMutation({
  mutationFn: downloadTrack,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tracks'] }),
});
```

### TypeScript
- Zawsze definiuj interfejsy dla props i odpowiedzi API
- Strict null checks — obsługuj `undefined` explicite
- `interface` dla obiektów, `type` dla union/aliases

### Performance
- `React.memo()` dla elementów list, `useMemo` dla computed data
- `React.lazy` + `Suspense` na poziomie route
- Throttle canvas renders (visualizer) do 60fps

## Audiovault-Specific

### Glassmorphism Theme
```css
backdrop-filter: blur(12px);
background: rgba(255,255,255,0.1);
border: 1px solid rgba(255,255,255,0.2);
```
6 color presets, dark mode default, CSS variables w `:root`

### WebSocket (Auto-Reconnect)
```typescript
const connectWS = (url: string) => {
  const ws = new WebSocket(url);
  ws.onclose = () => setTimeout(() => connectWS(url), 5000);
  return ws;
};
```

### Audio Visualizer
- Web Audio API → AnalyserNode → FFT → Canvas
- Synced do HTML5 Audio via `audioContext.createMediaElementSource`

## Commands
```bash
npm run dev      # Dev server (Vite)
npm run test     # Vitest
npm run format   # Prettier
npm run lint     # ESLint
npm run build    # Production
```

## Pułapki
- Brak `key` prop w listach → React warnings
- Zapomnienie `await` na mutacjach → silent failures
- `any` type → łamie type safety
- Brak invalidacji queries po mutacjach → stale UI
- Inline styles zamiast Tailwind → inconsistency
