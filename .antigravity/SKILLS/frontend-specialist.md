# Skill: Frontend Specialist (React/TypeScript)

## Role
You are an expert frontend developer specializing in React, TypeScript, and modern web development.

## Core Competencies

### React Best Practices
- Functional components with hooks
- Custom hooks for reusable logic
- Context API for global state
- React Query for server state
- Lazy loading and code splitting
- Memoization (useMemo, useCallback)
- Error boundaries

### TypeScript Patterns
```typescript
// Strict typing
interface Track {
  id: number;
  title: string;
  artist: string;
  album?: string;
  duration: number;
  filePath: string;
}

type TrackListProps = {
  tracks: Track[];
  onSelect: (track: Track) => void;
  loading?: boolean;
};

const TrackList: React.FC<TrackListProps> = ({ tracks, onSelect, loading = false }) => {
  // Component logic
};
```

### State Management
```typescript
// React Query for API calls
import { useQuery, useMutation } from '@tanstack/react-query';

const useTracks = () => {
  return useQuery({
    queryKey: ['tracks'],
    queryFn: async () => {
      const res = await fetch('/api/tracks');
      return res.json();
    },
  });
};

const useDownloadTrack = () => {
  return useMutation({
    mutationFn: async (url: string) => {
      const res = await fetch('/api/download', {
        method: 'POST',
        body: JSON.stringify({ url }),
      });
      return res.json();
    },
  });
};
```

### WebSocket Integration
```typescript
import { useEffect, useState } from 'react';

const useWebSocket = (url: string) => {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onmessage = (event) => {
      setData(JSON.parse(event.data));
    };
    
    return () => ws.close();
  }, [url]);
  
  return data;
};
```

### TailwindCSS v4
```tsx
// Modern utility-first styling
const Card = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-lg bg-white/10 backdrop-blur-lg p-6 shadow-xl border border-white/20 hover:bg-white/20 transition-all">
    {children}
  </div>
);
```

### Framer Motion Animations
```tsx
import { motion } from 'framer-motion';

const FadeIn = ({ children }: { children: React.ReactNode }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5 }}
  >
    {children}
  </motion.div>
);
```

## Component Patterns

### Custom Hooks
```typescript
// useAudioPlayer.ts
import { useState, useRef, useEffect } from 'react';

const useAudioPlayer = (src: string) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const toggle = () => {
    if (playing) {
      audioRef.current?.pause();
    } else {
      audioRef.current?.play();
    }
    setPlaying(!playing);
  };
  
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    
    const updateProgress = () => {
      setProgress((audio.currentTime / audio.duration) * 100);
    };
    
    audio.addEventListener('timeupdate', updateProgress);
    return () => audio.removeEventListener('timeupdate', updateProgress);
  }, []);
  
  return { audioRef, playing, progress, toggle };
};
```

### Error Boundaries
```typescript
import { Component, ReactNode } from 'react';

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  
  render() {
    if (this.state.hasError) {
      return <div>Something went wrong</div>;
    }
    return this.props.children;
  }
}
```

## Performance Optimization

### Code Splitting
```typescript
import { lazy, Suspense } from 'react';

const Library = lazy(() => import('./pages/Library'));

const App = () => (
  <Suspense fallback={<div>Loading...</div>}>
    <Library />
  </Suspense>
);
```

### Memoization
```typescript
import { memo, useMemo } from 'react';

const TrackItem = memo(({ track }: { track: Track }) => (
  <div>{track.title}</div>
));

const TrackList = ({ tracks }: { tracks: Track[] }) => {
  const sortedTracks = useMemo(
    () => [...tracks].sort((a, b) => a.title.localeCompare(b.title)),
    [tracks]
  );
  
  return (
    <div>
      {sortedTracks.map(track => <TrackItem key={track.id} track={track} />)}
    </div>
  );
};
```

## Debugging Tips
- Use React DevTools
- Check network tab for API calls
- Console.log sparingly (use debugger)
- Profile with React Profiler
- Test responsive design with DevTools

## Audiovault-Specific

### Audio Visualizer
- Uses Web Audio API
- Real-time FFT analysis
- Canvas rendering
- Synced to playback

### Theme System
- CSS variables for colors
- Dark mode by default
- 6 theme presets
- Glassmorphism effects

### Internationalization
- i18next integration
- 5 languages supported
- Dynamic locale switching
- Translation keys in JSON
