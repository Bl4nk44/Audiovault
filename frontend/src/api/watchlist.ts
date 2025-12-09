import api from "../services/api";
import type { WatchlistItem } from "../types";

export const watchlistApi = {
  getAll: async () => {
    const response = await api.get<WatchlistItem[]>("/watchlist/list");
    return response.data;
  },

  add: async (item: Omit<WatchlistItem, "id">) => {
    const response = await api.post<WatchlistItem>("/watchlist/add", item);
    return response.data;
  },

  remove: async (id: string) => {
    const response = await api.delete(`/watchlist/remove/${id}`);
    return response.data;
  },

  update: async (id: string, updates: { auto_download: boolean }) => {
    const response = await api.patch<WatchlistItem>(
      `/watchlist/${id}`,
      updates
    );
    return response.data;
  },

  checkUpdates: async () => {
    const response = await api.post<{
      status: string;
      new_downloads: number;
    }>("/watchlist/check-updates");
    return response.data;
  },
};
