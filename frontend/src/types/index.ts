export interface UserPreferences {
  theme?: "light" | "dark";
  language?: string;
  quality?: "low" | "normal" | "high" | "best";
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
  artist_id: string;
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
  title: string;
  description?: string;
  image_url?: string;
  tracks_count?: number;
  source: string;
  url?: string;
  type?: string; // Add type
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
