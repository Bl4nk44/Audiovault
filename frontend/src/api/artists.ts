import apiClient from './client';
import type { Artist } from '../types';

export const artistsApi = {
    getAll: async (skip = 0, limit = 50) => {
        const response = await apiClient.get<Artist[]>(`/artists?skip=${skip}&limit=${limit}`);
        return response.data;
    },

    getById: async (id: string) => {
        const response = await apiClient.get<Artist>(`/artists/${id}`);
        return response.data;
    },

    search: async (_query: string) => {
        // Fallback to metadata search or implement search endpoint
        // For now, let's assume we might search metadata if not found in DB
        // But backend artists.py doesn't have search yet.
        return [];
    }
};
