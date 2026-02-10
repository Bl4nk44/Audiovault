import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../services/api";
import { lyricsApi } from "./lyrics";

vi.mock("../services/api");

describe("Lyrics API", () => {
  const mockLyricsResponse = {
    found: true,
    lyrics: "La la la",
    title: "Song",
    artist: "Singer",
    url: "http://lyrics.com",
    album: "Album",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches lyrics by track ID", async () => {
    (api.get as any).mockResolvedValue({ data: mockLyricsResponse });

    const result = await lyricsApi.getByTrackId("123");

    expect(api.get).toHaveBeenCalledWith("/lyrics/track/123", {
      params: { use_cache: true },
    });
    expect(result).toEqual(mockLyricsResponse);
  });

  it("searches lyrics by artist and title", async () => {
    (api.get as any).mockResolvedValue({ data: mockLyricsResponse });

    const result = await lyricsApi.search("Queen", "Bohemian Rhapsody");

    expect(api.get).toHaveBeenCalledWith("/lyrics/search", {
      params: { artist: "Queen", title: "Bohemian Rhapsody", use_cache: true },
    });
    expect(result).toEqual(mockLyricsResponse);
  });

  it("handles api errors", async () => {
    (api.get as any).mockRejectedValue(new Error("API Error"));

    await expect(lyricsApi.getByTrackId("123")).rejects.toThrow("API Error");
  });
});
