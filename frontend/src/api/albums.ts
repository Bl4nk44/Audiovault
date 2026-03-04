import api from "../services/api";
import type { Track } from "../types";

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
  tracks: Track[];
  source: string;
  type: string;
}

export const albumsApi = {
  getById: async (id: string, source: string = "deezer"): Promise<AlbumDetails> => {
    const response = await api.get<AlbumDetails>(`/browse/album/${source}/${id}`);
    return response.data;
  },
};
