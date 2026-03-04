import { describe, it, expect, vi, beforeEach } from "vitest";
import { playlistsApi } from "./playlists";
import api from "../services/api";

vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

describe("playlistsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getById", () => {
    it("should fetch playlist from deezer endpoint by default", async () => {
      const mockPlaylist = {
        id: "pl-1",
        title: "Test Playlist",
        tracks: [],
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockPlaylist });

      const result = await playlistsApi.getById("pl-1");

      expect(api.get).toHaveBeenCalledWith("/browse/playlist/deezer/pl-1");
      expect(result).toEqual(mockPlaylist);
    });

    it("should fetch playlist from spotify when source is spotify", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: {} });

      await playlistsApi.getById("pl-1", "spotify");

      expect(api.get).toHaveBeenCalledWith("/browse/playlist/spotify/pl-1");
    });

    it("should fetch playlist from youtube when source is youtube", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: {} });

      await playlistsApi.getById("yt-pl-123", "youtube");

      expect(api.get).toHaveBeenCalledWith("/youtube/playlist/yt-pl-123");
    });
  });
});
