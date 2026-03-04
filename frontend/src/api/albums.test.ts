import { describe, it, expect, vi, beforeEach } from "vitest";
import { albumsApi } from "./albums";
import api from "../services/api";

vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

describe("albumsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getById", () => {
    it("should fetch album from browse endpoint using deezer by default", async () => {
      const mockAlbum = {
        id: "album-1",
        title: "Test Album",
        artist: "Test Artist",
        tracks: [],
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockAlbum });

      const result = await albumsApi.getById("album-1");

      expect(api.get).toHaveBeenCalledWith("/browse/album/deezer/album-1");
      expect(result).toEqual(mockAlbum);
    });

    it("should fetch album from browse endpoint when source is spotify", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { id: "album-1" } });

      await albumsApi.getById("album-1", "spotify");

      expect(api.get).toHaveBeenCalledWith("/browse/album/spotify/album-1");
    });
  });
});
