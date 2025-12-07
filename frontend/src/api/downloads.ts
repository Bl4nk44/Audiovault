import apiClient from './client';
import type { Download } from '../types';

export const downloadsApi = {
    getAll: async () => {
        const response = await apiClient.get<Download[]>('/downloads');
        return response.data;
    },

    pause: async (id: string) => {
        const response = await apiClient.post(`/downloads/${id}/pause`);
        return response.data;
    },

    resume: async (id: string) => {
        const response = await apiClient.post(`/downloads/${id}/resume`);
        return response.data;
    },

    retry: async (id: string) => {
        const response = await apiClient.post(`/downloads/${id}/retry`);
        return response.data;
    },

    remove: async (id: string) => {
        const response = await apiClient.delete(`/downloads/${id}`);
        return response.data;
    }
};
