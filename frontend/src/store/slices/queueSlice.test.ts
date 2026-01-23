import { beforeEach, describe, expect, it, Mock, vi } from "vitest";
import { downloadsApi } from "../../api/downloads";
import { createQueueSlice, type QueueSlice } from "./queueSlice";

// Mock downloadsApi
vi.mock("../../api/downloads", () => ({
  downloadsApi: {
    pause: vi.fn(),
    resume: vi.fn(),
    retry: vi.fn(),
    getAll: vi.fn(),
  },
}));

describe("queueSlice", () => {
  let state: QueueSlice;
  let set: (partial: Partial<QueueSlice> | ((state: QueueSlice) => Partial<QueueSlice>)) => void;
  let get: () => QueueSlice;

  beforeEach(() => {
    vi.clearAllMocks();

    set = (partial) => {
      if (typeof partial === "function") {
        Object.assign(state, partial(state));
      } else {
        Object.assign(state, partial);
      }
    };
    get = () => state;

    state = createQueueSlice(set, get, {} as never);
  });

  describe("initial state", () => {
    it("should have empty download queue", () => {
      expect(state.downloadQueue).toEqual([]);
    });
  });

  describe("addToQueue", () => {
    it("should add track to download queue", () => {
      const track = { id: "1", title: "Track 1" } as any;

      state.addToQueue(track);

      expect(state.downloadQueue).toHaveLength(1);
      expect(state.downloadQueue[0].track).toEqual(track);
      expect(state.downloadQueue[0].status).toBe("pending");
    });
  });

  describe("removeFromQueue", () => {
    it("should remove download from queue", () => {
      const track = { id: "1", title: "Track 1" } as any;
      state.addToQueue(track);
      const downloadId = state.downloadQueue[0].id;

      state.removeFromQueue(downloadId);

      expect(state.downloadQueue).toEqual([]);
    });
  });

  describe("updateProgress", () => {
    it("should update progress of a download", () => {
      const track = { id: "1", title: "Track 1" } as any;
      state.addToQueue(track);
      const downloadId = state.downloadQueue[0].id;

      state.updateProgress(downloadId, 50);

      expect(state.downloadQueue[0].progress).toBe(50);
    });
  });

  describe("updateStatus", () => {
    it("should update status of a download", () => {
      const track = { id: "1", title: "Track 1" } as any;
      state.addToQueue(track);
      const downloadId = state.downloadQueue[0].id;

      state.updateStatus(downloadId, "completed");

      expect(state.downloadQueue[0].status).toBe("completed");
    });
  });

  describe("async actions", () => {
    const track = { id: "1", title: "Track 1" } as any;
    let downloadId: string;

    beforeEach(() => {
      state.addToQueue(track);
      downloadId = state.downloadQueue[0].id;
    });

    it("pauseDownload should call api and update status optimistically", async () => {
      await state.pauseDownload(downloadId);

      expect(state.downloadQueue[0].status).toBe("paused");
      expect(downloadsApi.pause).toHaveBeenCalledWith(downloadId);
    });

    it("pauseDownload should handle errors", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      (downloadsApi.pause as Mock).mockRejectedValue(new Error("Fail"));

      await state.pauseDownload(downloadId);

      expect(consoleSpy).toHaveBeenCalledWith("Failed to pause", expect.any(Error));
      consoleSpy.mockRestore();
    });

    it("resumeDownload should call api and update status optimistically", async () => {
      state.updateStatus(downloadId, "paused");
      await state.resumeDownload(downloadId);

      expect(state.downloadQueue[0].status).toBe("pending");
      expect(downloadsApi.resume).toHaveBeenCalledWith(downloadId);
    });

    it("resumeDownload should handle errors", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      (downloadsApi.resume as Mock).mockRejectedValue(new Error("Fail"));

      await state.resumeDownload(downloadId);

      expect(consoleSpy).toHaveBeenCalledWith("Failed to resume", expect.any(Error));
      consoleSpy.mockRestore();
    });

    it("retryDownload should call api and update status optimistically", async () => {
      state.updateStatus(downloadId, "error", "Some error");

      await state.retryDownload(downloadId);

      expect(state.downloadQueue[0].status).toBe("pending");
      expect(state.downloadQueue[0].error).toBeUndefined();
      expect(downloadsApi.retry).toHaveBeenCalledWith(downloadId);
    });

    it("retryDownload should handle errors", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      (downloadsApi.retry as Mock).mockRejectedValue(new Error("Fail"));

      await state.retryDownload(downloadId);

      expect(consoleSpy).toHaveBeenCalledWith("Failed to retry", expect.any(Error));
      consoleSpy.mockRestore();
    });

    it("fetchDownloads should fetch and set queue", async () => {
      const mockDownloads = [{ id: "d1", track: {}, status: "completed" }];
      vi.mocked(downloadsApi.getAll).mockResolvedValue(mockDownloads as any);

      await state.fetchDownloads();

      expect(state.downloadQueue).toEqual(mockDownloads);
    });

    it("fetchDownloads should handle errors", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      (downloadsApi.getAll as Mock).mockRejectedValue(new Error("Fail"));

      await state.fetchDownloads();

      expect(consoleSpy).toHaveBeenCalledWith("Failed to fetch downloads", expect.any(Error));
      consoleSpy.mockRestore();
    });
  });
});
