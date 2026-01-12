import api from "../services/api";

export interface AlbumDetails {
  id: string;
  title: string;
  artist: string;
  artist_id: string;
  image_url: string | null;
  release_date: string | null;
  total_tracks: number;
  album_type: "album" | "single" | "compilation";
  label: string | null;
  tracks: Array<{
    id: string;
    title: string;
    artist: string;
    duration_ms: number;
    image_url: string | null;
    source: string;
  }>;
  source: string;
  type: string;
}

export const albumsApi = {
  getById: async (id: string, source: string = "spotify"): Promise<AlbumDetails> => {
    if (source === "spotify") {
      const response = await api.get<AlbumDetails>(`/spotify/album/${id}`);
      return response.data;
    }
    // Add other sources as needed
    throw new Error(`Unsupported source: ${source}`);
  },
};
