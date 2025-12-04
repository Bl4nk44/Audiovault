import { type StateCreator } from 'zustand'
import { type Track } from '../../types'

export interface PlayerSlice {
    currentTrack: Track | null
    isPlaying: boolean
    volume: number
    playTrack: (track: Track) => void
    togglePlay: () => void
    setVolume: (volume: number) => void
}

export const createPlayerSlice: StateCreator<PlayerSlice> = (set) => ({
    currentTrack: null,
    isPlaying: false,
    volume: 1,
    playTrack: (track) => set({ currentTrack: track, isPlaying: true }),
    togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
    setVolume: (volume) => set({ volume })
})
