import api from "../services/api";

export interface SyncReport {
  watchlist_id: string;
  watchlist_name: string;
  local_count: number;
  remote_count: number;
  to_add_count: number;
  to_remove_count: number;
  to_remove_items: Array<{
    track_id: string;
    title: string;
    artist: string;
    reason: string;
  }>;
  safety_warning: boolean;
  warning_message: string | null;
  sync_token: string;
  generated_at: string;
}

export interface SyncResult {
  status: string;
  removed_from_playlist: number;
  files_soft_deleted: number;
}

export const syncApi = {
  analyze: async (watchlistId: string): Promise<SyncReport> => {
    const response = await api.post(`/sync/${watchlistId}/analyze`);
    return response.data;
  },

  execute: async (
    watchlistId: string,
    syncToken: string,
    approvedRemovals: string[]
  ): Promise<SyncResult> => {
    const response = await api.post(`/sync/${watchlistId}/execute`, {
      sync_token: syncToken,
      approved_removals: approvedRemovals,
    });
    return response.data;
  },
};
