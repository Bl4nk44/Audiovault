import { describe, it, expect, vi, beforeEach } from "vitest";
import { syncApi } from "./sync";
import api from "../services/api";

vi.mock("../services/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

describe("syncApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("analyze", () => {
    it("should analyze watchlist for sync", async () => {
      const mockReport = {
        watchlist_id: "wl-1",
        watchlist_name: "Test Playlist",
        local_count: 10,
        remote_count: 12,
        to_add_count: 2,
        to_remove_count: 0,
        to_remove_items: [],
        safety_warning: false,
        warning_message: null,
        sync_token: "token-123",
        generated_at: "2026-01-20T12:00:00Z",
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockReport });

      const result = await syncApi.analyze("wl-1");

      expect(api.post).toHaveBeenCalledWith("/sync/wl-1/analyze");
      expect(result).toEqual(mockReport);
    });
  });

  describe("execute", () => {
    it("should execute sync with approved removals", async () => {
      const mockResult = {
        status: "completed",
        removed_from_playlist: 2,
        files_soft_deleted: 2,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResult });

      const result = await syncApi.execute("wl-1", "token-123", ["track-1", "track-2"]);

      expect(api.post).toHaveBeenCalledWith("/sync/wl-1/execute", {
        sync_token: "token-123",
        approved_removals: ["track-1", "track-2"],
      });
      expect(result).toEqual(mockResult);
    });

    it("should handle empty approved removals", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { status: "completed" } });

      await syncApi.execute("wl-1", "token-123", []);

      expect(api.post).toHaveBeenCalledWith("/sync/wl-1/execute", {
        sync_token: "token-123",
        approved_removals: [],
      });
    });
  });
});
