import api from "../services/api";
import type {
  Playlist,
  PlaylistCreateRequest,
  PlaylistTrackAddRequest,
  PlaylistUpdateRequest,
  Track,
} from "../types";

export interface PlaylistDetails extends Playlist {
  tracks: Track[];
}

export const playlistsApi = {
  // --- External Sources (Browse/YouTube) ---
  getById: async (id: string, source: string = "deezer") => {
    if (source === "youtube") {
      const response = await api.get<PlaylistDetails>(`/youtube/playlist/${id}`);
      return response.data;
    }
    if (source === "local") {
      return playlistsApi.getLocalById(id);
    }
    // Use browse for all other sources (spotify, deezer, etc.)
    const response = await api.get<PlaylistDetails>(`/browse/playlist/${source}/${id}`);
    return response.data;
  },

  // --- Local Backend Playlists (CRUD) ---

  create: async (data: PlaylistCreateRequest) => {
    const response = await api.post<Playlist>("/playlists/", data);
    return response.data;
  },

  getAll: async () => {
    const response = await api.get<Playlist[]>("/playlists/");
    // Map backend 'name' to 'title' for frontend compatibility if needed
    return response.data.map((p) => ({
      ...p,
      title: p.name,
      source: "local",
    }));
  },

  getLocalById: async (id: string) => {
    const response = await api.get<Playlist & { tracks: any[] }>(`/playlists/${id}`);
    // Transform backend tracks to frontend Track interface if structure differs
    const tracks: Track[] = response.data.tracks.map((t: any) => ({
      id: t.track_id,
      title: t.title,
      artist: t.artist,
      album: t.album,
      duration_ms: t.duration_ms,
      image_url: t.image_url,
      source: "local", // or preserve original source?
    }));

    return {
      ...response.data,
      title: response.data.name,
      source: "local",
      tracks,
    } as PlaylistDetails;
  },

  update: async (id: string, data: PlaylistUpdateRequest) => {
    const response = await api.put<Playlist>(`/playlists/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/playlists/${id}`);
  },

  addTracks: async (id: string, track_ids: string[]) => {
    const data: PlaylistTrackAddRequest = { track_ids };
    const response = await api.post<{
      added_count: number;
      duplicate_count: number;
      total_processed: number;
    }>(`/playlists/${id}/tracks`, data);
    return response.data;
  },

  removeTracks: async (id: string, trackIds: string[]) => {
    // Note: We use HTTP DELETE with body, axios supports it via 'data' config
    const data: PlaylistTrackAddRequest = { track_ids: trackIds };
    const response = await api.delete(`/playlists/${id}/tracks`, { data });
    return response.data;
  },

  /**
   * Export playlist as JSON file download.
   * Only works for local playlists.
   */
  exportAsJson: async (id: string, playlistName: string) => {
    const response = await api.get(`/playlists/${id}/export`, {
      responseType: "blob",
    });

    // Create a download link and trigger it
    const blob = new Blob([response.data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;

    // Create safe filename
    const safeName = playlistName.replaceAll(/[^a-z0-9\s\-_]/gi, "").trim();
    link.download = `${safeName || "playlist"}_export.json`;

    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
