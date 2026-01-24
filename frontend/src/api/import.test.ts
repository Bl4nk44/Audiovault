import { describe, it, expect, vi, beforeEach } from "vitest";
import { importApi } from "./import";
import api from "../services/api";

vi.mock("../services/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

describe("importApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("importPlaylist", () => {
    it("should import playlist by URL", async () => {
      const mockPlaylist = {
        title: "Imported Playlist",
        description: "Test description",
        tracks: [
          { title: "Track 1", artist: "Artist 1" },
          { title: "Track 2", artist: "Artist 2" },
        ],
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockPlaylist });

      const result = await importApi.importPlaylist("https://spotify.com/playlist/123");

      expect(api.post).toHaveBeenCalledWith("/import/playlist", {
        url: "https://spotify.com/playlist/123",
      });
      expect(result).toEqual(mockPlaylist);
    });
  });

  describe("resolve", () => {
    it("should resolve track metadata", async () => {
      const metadata = {
        title: "Song Title",
        artist: "Artist Name",
        album: "Album Name",
      };
      const resolvedTrack = {
        id: "resolved-id",
        title: "Song Title",
        artist: "Artist Name",
        album: "Album Name",
      };
      vi.mocked(api.post).mockResolvedValue({ data: resolvedTrack });

      const result = await importApi.resolve(metadata);

      expect(api.post).toHaveBeenCalledWith("/metadata/resolve", metadata);
      expect(result).toEqual(resolvedTrack);
    });
  });
});
