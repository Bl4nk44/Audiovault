export interface UserPreferences {
  theme?: "light" | "dark";
  language?: string;
  quality?: "low" | "normal" | "high" | "best" | "lossless";
  downloadPath?: string;
  avatar_url?: string;
  [key: string]: string | number | boolean | undefined;
}

export interface User {
  id: string;
  email: string;
  username: string;
  preferences: UserPreferences;
}

export interface Track {
  id: string;
  title: string;
  artist: string;
  cover?: string;
  image_url?: string;
  source: string;
  duration_ms?: number;
  artist_id?: string;
  spotify_artist_id?: string;
  album?: string;
  filename?: string;
  spotify_id?: string;
  youtube_id?: string;
  deezer_id?: string;
}

export interface Download {
  id: string;
  track: Track;
  progress: number;
  status: "pending" | "downloading" | "completed" | "failed" | "paused";
  error?: string;
  retry_count?: number;
  playlist_name?: string;
}

export interface WatchlistItem {
  id: string;
  user_id?: string;
  watch_type: "artist" | "playlist" | "channel";
  source: "spotify" | "youtube" | "deezer";
  source_id: string;
  source_name: string;
  auto_download: boolean;
  check_interval_hours?: number;
  last_checked_at?: string;
  new_items_count: number;
  created_at?: string;
  metadata_content?: {
    image_url?: string;
  };
}

export interface Album {
  id: string;
  title: string;
  release_date?: string;
  images?: Record<string, string>;
  image_url?: string;
  artist_id?: string;
  album_type?: "album" | "single" | "compilation";
  spotify_id?: string;
  total_tracks?: number;
}

export interface Artist {
  id: string;
  name: string;
  bio?: string;
  spotify_id?: string;
  deezer_id?: string;
  images?: Record<string, string>;
  image_url?: string; // Add image_url for search results
  albums?: Album[];
  tracks?: Track[];
  source?: string; // Add source
  type?: string; // Add type for search results
}

export interface Playlist {
  id: string;
  name: string; // Backend uses 'name', Spotify uses 'title' usually but we map it? No, backend playlist has 'name'.
  // But wait, existing frontend uses 'title'.
  // I should align them. Let's add 'name' as optional or use title.
  // The backend Pydantic model uses 'name'.
  // The existing frontend code uses 'title'.
  title: string; // Used for Spotify/YouTube

  description?: string; // Used for Spotify/YouTube
  comment?: string; // Used for Local Backend

  image_url?: string;
  tracks_count?: number;
  source: string; // 'local', 'spotify', 'youtube'
  url?: string;
  type?: string;

  // Backend specific
  public?: boolean;
  owner_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PlaylistCreateRequest {
  name: string;
  comment?: string;
  public?: boolean;
}

export interface PlaylistUpdateRequest {
  name?: string;
  comment?: string;
  public?: boolean;
}

export interface PlaylistTrackAddRequest {
  track_ids: string[];
}

export interface LoginCredentials {
  email?: string;
  password?: string;
  username?: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  username: string;
}
