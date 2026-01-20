import { describe, it, expect, vi, beforeEach } from "vitest";
import { downloadsApi } from "./downloads";
import api from "../services/api";

// Mock the api service
vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("downloadsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getAll", () => {
    it("should fetch downloads from queue endpoint", async () => {
      const mockDownloads = [{ id: "dl-1", status: "downloading" }];
      vi.mocked(api.get).mockResolvedValue({ data: mockDownloads });

      const result = await downloadsApi.getAll();

      expect(api.get).toHaveBeenCalledWith("/downloads/queue");
      expect(result).toEqual(mockDownloads);
    });
  });

  describe("getLibrary", () => {
    it("should fetch completed downloads from library endpoint", async () => {
      const mockLibrary = [{ id: "dl-1", status: "completed" }];
      vi.mocked(api.get).mockResolvedValue({ data: mockLibrary });

      const result = await downloadsApi.getLibrary();

      expect(api.get).toHaveBeenCalledWith("/downloads/library");
      expect(result).toEqual(mockLibrary);
    });
  });

  describe("add", () => {
    it("should add a download with correct payload", async () => {
      const payload = { track_id: "track-1", source: "spotify" };
      vi.mocked(api.post).mockResolvedValue({ data: { id: "new-dl" } });

      const result = await downloadsApi.add(payload);

      expect(api.post).toHaveBeenCalledWith("/downloads/add", payload);
      expect(result).toEqual({ id: "new-dl" });
    });

    it("should include playlist_name if provided", async () => {
      const payload = {
        track_id: "track-1",
        source: "spotify",
        playlist_name: "My Playlist",
      };
      vi.mocked(api.post).mockResolvedValue({ data: { id: "new-dl" } });

      await downloadsApi.add(payload);

      expect(api.post).toHaveBeenCalledWith("/downloads/add", payload);
    });
  });

  describe("pause", () => {
    it("should pause a specific download", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { success: true } });

      await downloadsApi.pause("dl-123");

      expect(api.post).toHaveBeenCalledWith("/downloads/dl-123/pause");
    });
  });

  describe("resume", () => {
    it("should resume a specific download", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { success: true } });

      await downloadsApi.resume("dl-123");

      expect(api.post).toHaveBeenCalledWith("/downloads/dl-123/resume");
    });
  });

  describe("retry", () => {
    it("should retry a specific download", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { success: true } });

      await downloadsApi.retry("dl-123");

      expect(api.post).toHaveBeenCalledWith("/downloads/dl-123/retry");
    });
  });

  describe("remove", () => {
    it("should delete a specific download", async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: { success: true } });

      await downloadsApi.remove("dl-123");

      expect(api.delete).toHaveBeenCalledWith("/downloads/dl-123");
    });
  });

  describe("restartAll", () => {
    it("should restart all downloads", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { restarted: 5 } });

      const result = await downloadsApi.restartAll();

      expect(api.post).toHaveBeenCalledWith("/downloads/restart-all");
      expect(result).toEqual({ restarted: 5 });
    });
  });

  describe("clearAll", () => {
    it("should clear download history", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { cleared: 10 } });

      const result = await downloadsApi.clearAll();

      expect(api.post).toHaveBeenCalledWith("/downloads/clear-history");
      expect(result).toEqual({ cleared: 10 });
    });
  });
});
