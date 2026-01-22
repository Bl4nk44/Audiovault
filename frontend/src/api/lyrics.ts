import api from "../services/api";

export interface LyricsResponse {
  found: boolean;
  lyrics: string | null;
  title: string | null;
  artist: string | null;
  url: string | null;
  album: string | null;
}

export const lyricsApi = {
  /**
   * Get lyrics for a track by its database ID.
   */
  getByTrackId: async (trackId: string): Promise<LyricsResponse> => {
    const response = await api.get<LyricsResponse>(`/lyrics/track/${trackId}`);
    return response.data;
  },

  /**
   * Search for lyrics by artist and title.
   */
  search: async (artist: string, title: string): Promise<LyricsResponse> => {
    const response = await api.get<LyricsResponse>("/lyrics/search", {
      params: { artist, title },
    });
    return response.data;
  },
};
