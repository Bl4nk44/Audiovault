import { create } from 'zustand'

interface User {
    id: string
    email: string
    username: string
    preferences: any
}

interface Track {
    id: string
    title: string
    artist: string
    cover?: string
    source: string
    duration?: number
}

interface AppState {
    user: User | null
    isAuthenticated: boolean
    token: string | null

    // Player State
    currentTrack: Track | null
    isPlaying: boolean
    volume: number

    setUser: (user: User | null) => void
    setToken: (token: string | null) => void
    logout: () => void

    // Player Actions
    playTrack: (track: Track) => void
    togglePlay: () => void
    setVolume: (volume: number) => void
}

export const useStore = create<AppState>((set) => ({
    user: null,
    isAuthenticated: !!localStorage.getItem('access_token'),
    token: localStorage.getItem('access_token'),

    currentTrack: null,
    isPlaying: false,
    volume: 1,

    setUser: (user) => set({ user }),
    setToken: (token) => {
        if (token) {
            localStorage.setItem('access_token', token)
        } else {
            localStorage.removeItem('access_token')
        }
        set({ token, isAuthenticated: !!token })
    },
    logout: () => {
        localStorage.removeItem('access_token')
        set({ user: null, token: null, isAuthenticated: false })
    },

    playTrack: (track) => set({ currentTrack: track, isPlaying: true }),
    togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
    setVolume: (volume) => set({ volume })
}))
