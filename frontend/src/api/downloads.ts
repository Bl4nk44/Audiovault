import api from "../services/api";
import type { Download } from "../types";

export const downloadsApi = {
  getAll: async () => {
    // Pointing to /queue to get active/pending/failed downloads
    const response = await api.get<Download[]>("/downloads/queue");
    return response.data;
  },

  getLibrary: async () => {
    // Fetch completed downloads
    const response = await api.get<Download[]>("/downloads/library");
    return response.data;
  },

  add: async (data: { track_id: string; source: string; playlist_name?: string }) => {
    const response = await api.post("/downloads/add", data);
    return response.data;
  },

  pause: async (id: string) => {
    const response = await api.post(`/downloads/${id}/pause`);
    return response.data;
  },

  resume: async (id: string) => {
    const response = await api.post(`/downloads/${id}/resume`);
    return response.data;
  },

  retry: async (id: string) => {
    const response = await api.post(`/downloads/${id}/retry`);
    return response.data;
  },

  remove: async (id: string) => {
    const response = await api.delete(`/downloads/${id}`);
    return response.data;
  },

  restartAll: async () => {
    const response = await api.post("/downloads/restart-all");
    return response.data;
  },

  clearAll: async () => {
    // Maps to clear-history but now essentially clears all non-active
    const response = await api.post("/downloads/clear-history");
    return response.data;
  },
};
