import { type StateCreator } from 'zustand'
import { type WatchlistItem } from '../../types'
import { watchlistApi } from '../../api/watchlist'

const WATCHLIST_STORAGE_KEY = 'audiovault_watchlist';

const loadFromStorage = (): WatchlistItem[] => {
    try {
        const stored = localStorage.getItem(WATCHLIST_STORAGE_KEY);
        if (!stored) return [];
        const parsed = JSON.parse(stored);
        return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
        return [];
    }
};

const saveToStorage = (watchlist: WatchlistItem[]) => {
    try {
        localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlist));
    } catch (e) {
        console.error("Failed to save watchlist to storage", e);
    }
};

export interface WatchlistSlice {
    watchlist: WatchlistItem[]
    syncWatchlist: () => Promise<void>
    addToWatchlist: (item: Omit<WatchlistItem, 'id'>) => Promise<void>
    removeFromWatchlist: (id: string) => Promise<void>
}

export const createWatchlistSlice: StateCreator<WatchlistSlice> = (set, get) => ({
    watchlist: loadFromStorage(),
    syncWatchlist: async () => {
        try {
            const items = await watchlistApi.getAll();
            if (Array.isArray(items)) {
                set({ watchlist: items });
                saveToStorage(items);
            } else {
                console.error('Sync failed: Received non-array watchlist', items);
            }
        } catch (error) {
            console.error('Failed to sync watchlist', error);
            // On error, we keep local storage state which acts as offline cache
        }
    },
    addToWatchlist: async (item) => {
        // Optimistic update (with temp ID if needed, but here we wait for API to be safe or use simple optimistic)
        try {
            const newItem = await watchlistApi.add(item);
            set((state) => {
                const updated = [...state.watchlist, newItem];
                saveToStorage(updated);
                return { watchlist: updated };
            });
        } catch (error) {
            console.error('Failed to add to watchlist', error);
        }
    },
    removeFromWatchlist: async (id) => {
        const previous = get().watchlist;
        // Optimistic
        set((state) => {
            const updated = state.watchlist.filter(i => i.id !== id);
            saveToStorage(updated);
            return { watchlist: updated };
        });

        try {
            await watchlistApi.remove(id);
        } catch (error) {
            console.error('Failed to remove from watchlist', error);
            set({ watchlist: previous }); // Revert
            saveToStorage(previous);
        }
    }
})
