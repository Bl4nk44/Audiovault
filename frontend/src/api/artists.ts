import api from "../services/api";
import type { Artist } from "../types";

export const artistsApi = {
  getAll: async (skip = 0, limit = 50) => {
    const response = await api.get<Artist[]>(`/artists?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  getById: async (id: string, source: string = "deezer") => {
    // Use browse endpoint for external sources (routes to SearchOrchestrator)
    if (source !== "local") {
      const response = await api.get<Artist>(`/browse/artist/${source}/${id}`);
      return response.data;
    }

    // Default to local/generic endpoint (which expects UUID)
    const response = await api.get<Artist>(`/artists/${id}`);
    return response.data;
  },
};
