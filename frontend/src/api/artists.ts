import api from "../services/api";
import type { Artist } from "../types";

export const artistsApi = {
  getAll: async (skip = 0, limit = 50) => {
    const response = await api.get<Artist[]>(
      `/artists?skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  getById: async (id: string) => {
    const response = await api.get<Artist>(`/artists/${id}`);
    return response.data;
  },
};
