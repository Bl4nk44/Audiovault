import api from "../services/api";
import type { Playlist, Track } from "../types";

export interface PlaylistDetails extends Playlist {
  tracks: Track[];
  description?: string;
}

export const playlistsApi = {
  getById: async (id: string, source: string = "spotify") => {
    // Phase 2: Integrated YouTube
    if (source === "spotify") {
      const response = await api.get<PlaylistDetails>(
        `/spotify/playlist/${id}`
      );
      return response.data;
    }

    if (source === "youtube") {
      const response = await api.get<PlaylistDetails>(
        `/youtube/playlist/${id}`
      );
      return response.data;
    }

    // Default fallback to spotify if source not recognized (or add others)
    throw new Error(`Source ${source} not supported yet for playlist details`);
  },
};
