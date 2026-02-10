import type { LastfmProfile, LastfmStatus, RecommendationResponse } from "../types/lastfm";
import api from "./api";

export const connectLastfm = async (): Promise<{ auth_url: string }> => {
  const { data } = await api.get("/lastfm/connect");
  return data;
};

export const callbackLastfm = async (token: string): Promise<void> => {
  await api.get(`/lastfm/callback?token=${token}`);
};

export const disconnectLastfm = async (): Promise<void> => {
  await api.post("/lastfm/disconnect");
};

export const getLastfmStatus = async (): Promise<LastfmStatus> => {
  const { data } = await api.get<LastfmStatus>("/lastfm/status");
  return data;
};

export const getRecommendations = async (forceRefresh = false): Promise<RecommendationResponse> => {
  const { data } = await api.get<RecommendationResponse>("/lastfm/recommendations", {
    params: { force_refresh: forceRefresh },
  });
  return data;
};

export const scrobbleNowPlaying = async (track: string, artist: string, album?: string) => {
  // Fire and forget or handle error quietly
  try {
    await api.post("/lastfm/scrobble/now_playing", { track, artist, album });
  } catch (e) {
    console.warn("Failed to update now playing", e);
  }
};

export const scrobbleTrack = async (
  track: string,
  artist: string,
  timestamp?: number,
  album?: string
) => {
  try {
    await api.post("/lastfm/scrobble", { track, artist, timestamp, album });
  } catch (e) {
    console.warn("Failed to scrobble", e);
  }
};

export const getLastfmProfile = async (): Promise<LastfmProfile> => {
  const { data } = await api.get<LastfmProfile>("/lastfm/profile");
  return data;
};
