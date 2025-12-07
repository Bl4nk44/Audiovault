import apiClient from './client';
import type { WatchlistItem } from '../types';

export const watchlistApi = {
    getAll: async () => {
        const response = await apiClient.get<WatchlistItem[]>('/watchlist/list');
        return response.data;
    },

    add: async (item: Omit<WatchlistItem, 'id'>) => {
        const response = await apiClient.post<WatchlistItem>('/watchlist/add', item);
        return response.data;
    },

    remove: async (id: string) => {
        const response = await apiClient.delete(`/watchlist/remove/${id}`);
        return response.data;
    },

    update: async (id: string, updates: { auto_download: boolean }) => {
        const response = await apiClient.patch<WatchlistItem>(`/watchlist/${id}`, updates);
        return response.data;
    },

    checkUpdates: async () => {
        const response = await apiClient.post<{ status: string, new_downloads: number }>('/watchlist/check-updates');
        return response.data;
    }
};
