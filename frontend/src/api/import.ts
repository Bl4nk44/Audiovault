import api from "../services/api";
// type import removed

export interface TrackMetadata {
  title: string;
  artist: string;
  album?: string;
  duration_ms?: number;
  source_id?: string;
  source_url?: string;
  image_url?: string;
}

export interface PlaylistMetadata {
  title: string;
  description?: string;
  author?: string;
  tracks: TrackMetadata[];
}

export const importApi = {
  importPlaylist: async (url: string) => {
    const response = await api.post<PlaylistMetadata>("/import/playlist", {
      url,
    });
    return response.data;
  },

  resolve: async (metadata: TrackMetadata) => {
    const response = await api.post<{
      id: string;
      title: string;
      artist: string;
      album: string;
    }>("/metadata/resolve", metadata);
    return response.data;
  },
};
