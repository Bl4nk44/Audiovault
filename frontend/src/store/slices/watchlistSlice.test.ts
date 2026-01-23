import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WatchlistItem } from "../../types";
import { createWatchlistSlice, type WatchlistSlice } from "./watchlistSlice";

// Mock the watchlist API
vi.mock("../../api/watchlist", () => ({
  watchlistApi: {
    getAll: vi.fn(),
    add: vi.fn(),
    remove: vi.fn(),
  },
}));

// localStorage is mocked globally in setupTests.ts
const localStorageMock = globalThis.localStorage as any;

import { watchlistApi } from "../../api/watchlist";

describe("watchlistSlice", () => {
  let state: WatchlistSlice;
  let set: (
    partial: Partial<WatchlistSlice> | ((state: WatchlistSlice) => Partial<WatchlistSlice>)
  ) => void;
  let get: () => WatchlistSlice;

  const mockWatchlistItem: WatchlistItem = {
    id: "wl-1",
    watch_type: "artist",
    source: "spotify",
    source_id: "spotify-artist-123",
    source_name: "Test Artist",
    auto_download: true,
    new_items_count: 5,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);

    set = (partial) => {
      if (typeof partial === "function") {
        Object.assign(state, partial(state));
      } else {
        Object.assign(state, partial);
      }
    };
    get = () => state;

    state = createWatchlistSlice(set, get, {} as never);
  });

  describe("initial state", () => {
    it("should load empty watchlist when localStorage is empty", () => {
      expect(state.watchlist).toEqual([]);
    });

    it("should load watchlist from localStorage if available", () => {
      localStorageMock.getItem.mockReturnValue(JSON.stringify([mockWatchlistItem]));

      state = createWatchlistSlice(set, get, {} as never);

      expect(state.watchlist).toEqual([mockWatchlistItem]);
    });

    it("should handle corrupt localStorage data", () => {
      localStorageMock.getItem.mockReturnValue("invalid-json");
      state = createWatchlistSlice(set, get, {} as never);
      expect(state.watchlist).toEqual([]);
    });
  });

  describe("syncWatchlist", () => {
    it("should fetch and update watchlist from API", async () => {
      vi.mocked(watchlistApi.getAll).mockResolvedValue([mockWatchlistItem]);

      await state.syncWatchlist();

      expect(state.watchlist).toEqual([mockWatchlistItem]);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "audiovault_watchlist",
        JSON.stringify([mockWatchlistItem])
      );
    });

    it("should handle non-array response from API", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      vi.mocked(watchlistApi.getAll).mockResolvedValue({ error: "bad" } as any);

      await state.syncWatchlist();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining("Sync failed"),
        expect.any(Object)
      );
      consoleSpy.mockRestore();
    });

    it("should handle API errors and keep local state", async () => {
      state.watchlist = [mockWatchlistItem];
      vi.mocked(watchlistApi.getAll).mockRejectedValue(new Error("Network error"));
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      await state.syncWatchlist();

      expect(state.watchlist).toEqual([mockWatchlistItem]);
      consoleSpy.mockRestore();
    });
  });

  describe("addToWatchlist", () => {
    it("should add item to watchlist after API call", async () => {
      const newItem = { ...mockWatchlistItem };
      vi.mocked(watchlistApi.add).mockResolvedValue(newItem);

      await state.addToWatchlist({
        watch_type: "artist",
        source: "spotify",
        source_id: "spotify-artist-123",
        source_name: "Test Artist",
        auto_download: true,
        new_items_count: 5,
      });

      expect(state.watchlist).toContainEqual(newItem);
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it("should handle API errors gracefully", async () => {
      vi.mocked(watchlistApi.add).mockRejectedValue(new Error("Failed"));
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      await state.addToWatchlist({
        watch_type: "artist",
        source: "spotify",
        source_id: "test",
        source_name: "Test",
        auto_download: true,
        new_items_count: 0,
      });

      expect(state.watchlist).toEqual([]);
      consoleSpy.mockRestore();
    });
  });

  describe("removeFromWatchlist", () => {
    it("should optimistically remove item from watchlist", async () => {
      state.watchlist = [mockWatchlistItem];
      vi.mocked(watchlistApi.remove).mockResolvedValue({});

      await state.removeFromWatchlist("wl-1");

      expect(state.watchlist).toEqual([]);
    });

    it("should revert on API error", async () => {
      state.watchlist = [mockWatchlistItem];
      vi.mocked(watchlistApi.remove).mockRejectedValue(new Error("Failed"));
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      await state.removeFromWatchlist("wl-1");

      // Should revert to original state
      expect(state.watchlist).toEqual([mockWatchlistItem]);
      consoleSpy.mockRestore();
    });
  });

  describe("storage errors", () => {
    it("should handle storage setItem errors", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error("Storage full");
      });

      state.watchlist = [];
      vi.mocked(watchlistApi.getAll).mockResolvedValue([mockWatchlistItem]);
      await state.syncWatchlist();

      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to save watchlist to storage",
        expect.any(Error)
      );
      consoleSpy.mockRestore();
    });
  });
});
