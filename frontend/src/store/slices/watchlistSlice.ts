import { type StateCreator } from 'zustand'
import { type WatchlistItem } from '../../types'

export interface WatchlistSlice {
    watchlist: WatchlistItem[]
    addToWatchlist: (item: WatchlistItem) => void
    removeFromWatchlist: (id: string) => void
}

export const createWatchlistSlice: StateCreator<WatchlistSlice> = (set) => ({
    watchlist: [],
    addToWatchlist: (item) => set((state) => ({
        watchlist: [...state.watchlist, item]
    })),
    removeFromWatchlist: (id) => set((state) => ({
        watchlist: state.watchlist.filter(i => i.id !== id)
    }))
})
