import { type StateCreator } from "zustand";
import { type Track } from "../../types";

export type VisualizerMode = "classic" | "mirror" | "spectrum" | "pulse" | "glow";

export interface PlayerSlice {
  currentTrack: Track | null;
  isPlaying: boolean;
  volume: number;
  queue: Track[];
  currentTrackIndex: number;
  playTrack: (track: Track, queue?: Track[]) => void;
  togglePlay: () => void;
  setVolume: (volume: number) => void;
  nextTrack: () => void;
  prevTrack: () => void;
  addToQueue: (track: Track) => void;
  visualizerMode: VisualizerMode;
  setVisualizerMode: (mode: VisualizerMode) => void;
}

export const createPlayerSlice: StateCreator<PlayerSlice> = (set, get) => ({
  currentTrack: null,
  isPlaying: false,
  volume: 1,
  queue: [],
  currentTrackIndex: -1,
  playTrack: (track, queue) =>
    set({
      currentTrack: track,
      isPlaying: true,
      queue: queue || [track],
      currentTrackIndex: queue ? queue.findIndex((t) => t.id === track.id) : 0,
    }),
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  setVolume: (volume) => set({ volume }),
  nextTrack: () => {
    const { queue, currentTrackIndex } = get();
    if (currentTrackIndex < queue.length - 1) {
      const nextIndex = currentTrackIndex + 1;
      set({
        currentTrack: queue[nextIndex],
        currentTrackIndex: nextIndex,
        isPlaying: true,
      });
    }
  },
  prevTrack: () => {
    const { queue, currentTrackIndex } = get();
    if (currentTrackIndex > 0) {
      const prevIndex = currentTrackIndex - 1;
      set({
        currentTrack: queue[prevIndex],
        currentTrackIndex: prevIndex,
        isPlaying: true,
      });
    }
  },
  addToQueue: (track) => set((state) => ({ queue: [...state.queue, track] })),
  visualizerMode: "classic",
  setVisualizerMode: (mode) => set({ visualizerMode: mode }),
});
