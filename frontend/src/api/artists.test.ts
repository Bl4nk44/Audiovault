import { describe, it, expect, vi, beforeEach } from "vitest";
import { artistsApi } from "./artists";
import api from "../services/api";

vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

describe("artistsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getAll", () => {
    it("should fetch artists with default pagination", async () => {
      const mockArtists = [{ id: "a-1", name: "Artist 1" }];
      vi.mocked(api.get).mockResolvedValue({ data: mockArtists });

      const result = await artistsApi.getAll();

      expect(api.get).toHaveBeenCalledWith("/artists?skip=0&limit=50");
      expect(result).toEqual(mockArtists);
    });

    it("should fetch artists with custom pagination", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await artistsApi.getAll(10, 25);

      expect(api.get).toHaveBeenCalledWith("/artists?skip=10&limit=25");
    });
  });

  describe("getById", () => {
    it("should fetch artist by id using deezer endpoint by default", async () => {
      const mockArtist = { id: "a-1", name: "Test Artist" };
      vi.mocked(api.get).mockResolvedValue({ data: mockArtist });

      const result = await artistsApi.getById("a-1");

      expect(api.get).toHaveBeenCalledWith("/browse/artist/deezer/a-1");
      expect(result).toEqual(mockArtist);
    });

    it("should fetch artist from browse endpoint when source is spotify", async () => {
      const mockArtist = { id: "sp-artist", name: "Spotify Artist" };
      vi.mocked(api.get).mockResolvedValue({ data: mockArtist });

      const result = await artistsApi.getById("sp-artist", "spotify");

      expect(api.get).toHaveBeenCalledWith("/browse/artist/spotify/sp-artist");
      expect(result).toEqual(mockArtist);
    });

    it("should use local endpoint for local source", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: {} });

      await artistsApi.getById("local-123", "local");

      expect(api.get).toHaveBeenCalledWith("/artists/local-123");
    });
  });
});
