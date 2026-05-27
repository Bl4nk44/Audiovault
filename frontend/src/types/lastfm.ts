export interface RecommendedTrack {
  name: string;
  artist: string;
  url: string;
  image_url: string | null;
  mbid: string | null;
  score: number;
  match: number;
  playcount: number;
  reason: string | null;
}

export interface RecommendedArtist {
  name: string;
  url: string;
  image_url: string | null;
  mbid: string | null;
  match: number;
  rank: number | null;
  tags: string[];
}

export interface RecommendedPlaylist {
  id: string;
  title: string;
  description: string | null;
  image_url: string | null;
  track_count: number;
  source: string;
  url: string | null;
}

export interface RecommendationResponse {
  tracks: RecommendedTrack[];
  artists: RecommendedArtist[];
  playlists: RecommendedPlaylist[];
  source: string;
  cache_status: string;
  lastfm_connected: boolean;
  generated_at: string;
}

export interface LastfmStatus {
  connected: boolean;
  username: string | null;
}

export interface LastfmUserInfo {
  name: string;
  realname: string;
  url: string;
  country: string;
  age: number;
  playcount: number;
  artist_count: number;
  track_count: number;
  album_count: number;
  image_url: string | null;
  registered: number;
  subscriber: boolean;
}

export interface LastfmFriend {
  name: string;
  realname: string;
  url: string;
  country: string;
  image_url: string | null;
}

export interface LastfmProfile {
  user: LastfmUserInfo;
  friends: LastfmFriend[];
}
