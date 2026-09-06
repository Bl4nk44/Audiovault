import { describe, expect, it, vi } from "vitest";
import api from "./api";
import * as listening from "./listening";

vi.mock("./api", () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}));

describe("listening service", () => {
  it("getProviders hits /listening/providers", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { preference: "auto", providers: [] } });
    const r = await listening.getProviders();
    expect(api.get).toHaveBeenCalledWith("/listening/providers");
    expect(r.preference).toBe("auto");
  });

  it("connectRedirectProvider posts to /listening/connect/{provider}", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { auth_url: "http://auth" } });
    const r = await listening.connectRedirectProvider("lastfm");
    expect(api.post).toHaveBeenCalledWith("/listening/connect/lastfm");
    expect(r.auth_url).toBe("http://auth");
  });

  it("connectTokenProvider posts token body", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: { username: "alice" } });
    const r = await listening.connectTokenProvider("listenbrainz", "tok");
    expect(api.post).toHaveBeenCalledWith("/listening/connect/listenbrainz", { token: "tok" });
    expect(r.username).toBe("alice");
  });

  it("disconnectProvider posts to /listening/disconnect/{provider}", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    await listening.disconnectProvider("listenbrainz");
    expect(api.post).toHaveBeenCalledWith("/listening/disconnect/listenbrainz");
  });

  it("setListeningPreference PUTs the preference", async () => {
    vi.mocked(api.put).mockResolvedValue({ data: {} });
    await listening.setListeningPreference("listenbrainz");
    expect(api.put).toHaveBeenCalledWith("/listening/preference", {
      listening_provider: "listenbrainz",
    });
  });

  it("scrobbleNowPlaying swallows errors", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("net"));
    await expect(listening.scrobbleNowPlaying("T", "A", "Alb")).resolves.toBeUndefined();
    expect(api.post).toHaveBeenCalledWith("/listening/scrobble/now_playing", {
      track: "T",
      artist: "A",
      album: "Alb",
    });
  });

  it("scrobbleTrack swallows errors and passes timestamp", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    await listening.scrobbleTrack("T", "A", 123, "Alb");
    expect(api.post).toHaveBeenCalledWith("/listening/scrobble", {
      track: "T",
      artist: "A",
      timestamp: 123,
      album: "Alb",
    });
  });
});
