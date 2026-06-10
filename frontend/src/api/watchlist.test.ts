import { describe, it, expect, vi, beforeEach } from "vitest";
import { watchlistApi } from "./watchlist";
import api from "../services/api";

// Mock the api service
vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  },
}));

describe("watchlistApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getAll", () => {
    it("should fetch watchlist from list endpoint", async () => {
      const mockWatchlist = [{ id: "wl-1", source_name: "Artist" }];
      vi.mocked(api.get).mockResolvedValue({ data: mockWatchlist });

      const result = await watchlistApi.getAll();

      expect(api.get).toHaveBeenCalledWith("/watchlist/list");
      expect(result).toEqual(mockWatchlist);
    });
  });

  describe("add", () => {
    it("should add item to watchlist", async () => {
      const newItem = {
        watch_type: "artist" as const,
        source: "spotify" as const,
        source_id: "sp-123",
        source_name: "Test Artist",
        auto_download: true,
        auto_sync_deletions: false,
        new_items_count: 0,
      };
      const responseItem = { ...newItem, id: "wl-new" };
      vi.mocked(api.post).mockResolvedValue({ data: responseItem });

      const result = await watchlistApi.add(newItem);

      expect(api.post).toHaveBeenCalledWith("/watchlist/add", newItem);
      expect(result).toEqual(responseItem);
    });
  });

  describe("remove", () => {
    it("should remove item from watchlist", async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: { success: true } });

      await watchlistApi.remove("wl-123");

      expect(api.delete).toHaveBeenCalledWith("/watchlist/remove/wl-123");
    });
  });

  describe("update", () => {
    it("should update watchlist item with new settings", async () => {
      const updates = { auto_download: false };
      const updatedItem = { id: "wl-123", auto_download: false };
      vi.mocked(api.patch).mockResolvedValue({ data: updatedItem });

      const result = await watchlistApi.update("wl-123", updates);

      expect(api.patch).toHaveBeenCalledWith("/watchlist/wl-123", updates);
      expect(result).toEqual(updatedItem);
    });
  });

  describe("checkUpdates", () => {
    it("should trigger update check", async () => {
      const response = { status: "completed", new_downloads: 5 };
      vi.mocked(api.post).mockResolvedValue({ data: response });

      const result = await watchlistApi.checkUpdates();

      expect(api.post).toHaveBeenCalledWith("/watchlist/check-updates");
      expect(result).toEqual(response);
    });
  });
});
