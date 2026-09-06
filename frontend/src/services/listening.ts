import type { ProvidersResponse } from "../types/listening";
import api from "./api";

export const getProviders = async (): Promise<ProvidersResponse> => {
  const { data } = await api.get<ProvidersResponse>("/listening/providers");
  return data;
};

/** Redirect-flow providers (Last.fm): returns the URL to open in the browser. */
export const connectRedirectProvider = async (provider: string): Promise<{ auth_url: string }> => {
  const { data } = await api.post(`/listening/connect/${provider}`);
  return data;
};

/** Token-paste providers (ListenBrainz): validates and stores the token. */
export const connectTokenProvider = async (
  provider: string,
  token: string
): Promise<{ username: string }> => {
  const { data } = await api.post(`/listening/connect/${provider}`, { token });
  return data;
};

export const disconnectProvider = async (provider: string): Promise<void> => {
  await api.post(`/listening/disconnect/${provider}`);
};

export const setListeningPreference = async (listeningProvider: string): Promise<void> => {
  await api.put("/listening/preference", { listening_provider: listeningProvider });
};

/** Fire-and-forget: fans out to every connected provider server-side. */
export const scrobbleNowPlaying = async (track: string, artist: string, album?: string) => {
  try {
    await api.post("/listening/scrobble/now_playing", { track, artist, album });
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
    await api.post("/listening/scrobble", { track, artist, timestamp, album });
  } catch (e) {
    console.warn("Failed to scrobble", e);
  }
};
