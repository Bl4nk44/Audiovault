import { describe, expect, it, vi } from "vitest";
import api from "./api";
import * as lastfmService from "./lastfm";

vi.mock("./api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("lastfmService", () => {
  it("connectLastfm should call /lastfm/connect", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { auth_url: "http://auth" } });
    const result = await lastfmService.connectLastfm();
    expect(api.get).toHaveBeenCalledWith("/lastfm/connect");
    expect(result.auth_url).toBe("http://auth");
  });

  it("callbackLastfm should call /lastfm/callback", async () => {
    await lastfmService.callbackLastfm("token123");
    expect(api.get).toHaveBeenCalledWith("/lastfm/callback?token=token123");
  });

  it("disconnectLastfm should call /lastfm/disconnect", async () => {
    await lastfmService.disconnectLastfm();
    expect(api.post).toHaveBeenCalledWith("/lastfm/disconnect");
  });

  it("getLastfmStatus should return status data", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { connected: true } });
    const result = await lastfmService.getLastfmStatus();
    expect(api.get).toHaveBeenCalledWith("/lastfm/status");
    expect(result.connected).toBe(true);
  });

  it("getRecommendations should pass force_refresh param", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { tracks: [] } });
    await lastfmService.getRecommendations(true);
    expect(api.get).toHaveBeenCalledWith("/lastfm/recommendations", {
      params: { force_refresh: true },
    });
  });

  it("scrobbleNowPlaying should handle success", async () => {
    await lastfmService.scrobbleNowPlaying("Track", "Artist", "Album");
    expect(api.post).toHaveBeenCalledWith("/lastfm/scrobble/now_playing", {
      track: "Track",
      artist: "Artist",
      album: "Album",
    });
  });

  it("scrobbleNowPlaying should handle error silently", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("API Error"));
    const spy = vi.spyOn(console, "warn").mockImplementation(() => {});
    await lastfmService.scrobbleNowPlaying("Track", "Artist");
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });

  it("scrobbleTrack should handle success", async () => {
    await lastfmService.scrobbleTrack("Track", "Artist", 123456, "Album");
    expect(api.post).toHaveBeenCalledWith("/lastfm/scrobble", {
      track: "Track",
      artist: "Artist",
      timestamp: 123456,
      album: "Album",
    });
  });

  it("getLastfmProfile should return profile data", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { user: { name: "User" }, friends: [] } });
    const result = await lastfmService.getLastfmProfile();
    expect(api.get).toHaveBeenCalledWith("/lastfm/profile");
    expect(result.user.name).toBe("User");
  });
});
