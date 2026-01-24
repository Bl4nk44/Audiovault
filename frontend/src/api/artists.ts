import api from "../services/api";
import type { Artist } from "../types";

export const artistsApi = {
  getAll: async (skip = 0, limit = 50) => {
    const response = await api.get<Artist[]>(`/artists?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  getById: async (id: string, source: string = "local") => {
    // If source is spotify, use the spotify-specific endpoint
    if (source === "spotify") {
      const response = await api.get<Artist>(`/spotify/artist/${id}`);
      return response.data;
    }

    // Default to local/generic endpoint (which expects UUID)
    // If source is 'youtube', we will implement that in Phase 2

    const response = await api.get<Artist>(`/artists/${id}`);
    return response.data;
  },
};
