import { describe, it, expect, beforeEach, vi } from "vitest";
import { createQueueSlice, type QueueSlice } from "./queueSlice";
import type { Download, Track } from "../../types";

// Mock the downloads API
vi.mock("../../api/downloads", () => ({
  downloadsApi: {
    getAll: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    retry: vi.fn(),
  },
}));

import { downloadsApi } from "../../api/downloads";

describe("queueSlice", () => {
  let state: QueueSlice;
  let set: (
    partial: Partial<QueueSlice> | ((state: QueueSlice) => Partial<QueueSlice>),
  ) => void;

  const mockTrack: Track = {
    id: "track-1",
    title: "Test Track",
    artist: "Test Artist",
    source: "spotify",
  };

  const mockDownload: Download = {
    id: "dl-1",
    track: mockTrack,
    progress: 50,
    status: "downloading",
  };

  beforeEach(() => {
    vi.clearAllMocks();

    set = (partial) => {
      if (typeof partial === "function") {
        Object.assign(state, partial(state));
      } else {
        Object.assign(state, partial);
      }
    };

    state = createQueueSlice(set, () => state, {} as never);
  });

  describe("initial state", () => {
    it("should have empty downloadQueue", () => {
      expect(state.downloadQueue).toEqual([]);
    });
  });

  describe("addToQueue", () => {
    it("should add track to download queue", () => {
      state.addToQueue(mockTrack);

      expect(state.downloadQueue).toHaveLength(1);
      expect(state.downloadQueue[0].track).toEqual(mockTrack);
      expect(state.downloadQueue[0].status).toBe("pending");
      expect(state.downloadQueue[0].progress).toBe(0);
    });

    it("should generate unique IDs", () => {
      state.addToQueue(mockTrack);
      state.addToQueue(mockTrack);

      expect(state.downloadQueue[0].id).not.toBe(state.downloadQueue[1].id);
    });
  });

  describe("removeFromQueue", () => {
    it("should remove download from queue by id", () => {
      state.downloadQueue = [mockDownload];

      state.removeFromQueue("dl-1");

      expect(state.downloadQueue).toHaveLength(0);
    });

    it("should not affect other downloads", () => {
      const download2: Download = { ...mockDownload, id: "dl-2" };
      state.downloadQueue = [mockDownload, download2];

      state.removeFromQueue("dl-1");

      expect(state.downloadQueue).toHaveLength(1);
      expect(state.downloadQueue[0].id).toBe("dl-2");
    });
  });

  describe("updateProgress", () => {
    it("should update progress for specific download", () => {
      state.downloadQueue = [mockDownload];

      state.updateProgress("dl-1", 75);

      expect(state.downloadQueue[0].progress).toBe(75);
    });

    it("should not affect other downloads", () => {
      const download2: Download = { ...mockDownload, id: "dl-2", progress: 25 };
      state.downloadQueue = [mockDownload, download2];

      state.updateProgress("dl-1", 100);

      expect(state.downloadQueue[0].progress).toBe(100);
      expect(state.downloadQueue[1].progress).toBe(25);
    });
  });

  describe("updateStatus", () => {
    it("should update status for specific download", () => {
      state.downloadQueue = [mockDownload];

      state.updateStatus("dl-1", "completed");

      expect(state.downloadQueue[0].status).toBe("completed");
    });

    it("should set error message when provided", () => {
      state.downloadQueue = [mockDownload];

      state.updateStatus("dl-1", "failed", "Network error");

      expect(state.downloadQueue[0].status).toBe("failed");
      expect(state.downloadQueue[0].error).toBe("Network error");
    });
  });

  describe("pauseDownload", () => {
    it("should optimistically set status to paused", async () => {
      state.downloadQueue = [mockDownload];
      vi.mocked(downloadsApi.pause).mockResolvedValue({});

      await state.pauseDownload("dl-1");

      expect(state.downloadQueue[0].status).toBe("paused");
    });

    it("should call API to pause", async () => {
      state.downloadQueue = [mockDownload];
      vi.mocked(downloadsApi.pause).mockResolvedValue({});

      await state.pauseDownload("dl-1");

      expect(downloadsApi.pause).toHaveBeenCalledWith("dl-1");
    });
  });

  describe("resumeDownload", () => {
    it("should optimistically set status to pending", async () => {
      const pausedDownload: Download = { ...mockDownload, status: "paused" };
      state.downloadQueue = [pausedDownload];
      vi.mocked(downloadsApi.resume).mockResolvedValue({});

      await state.resumeDownload("dl-1");

      expect(state.downloadQueue[0].status).toBe("pending");
    });

    it("should call API to resume", async () => {
      state.downloadQueue = [mockDownload];
      vi.mocked(downloadsApi.resume).mockResolvedValue({});

      await state.resumeDownload("dl-1");

      expect(downloadsApi.resume).toHaveBeenCalledWith("dl-1");
    });
  });

  describe("retryDownload", () => {
    it("should optimistically set status to pending and clear error", async () => {
      const failedDownload: Download = {
        ...mockDownload,
        status: "failed",
        error: "Some error",
      };
      state.downloadQueue = [failedDownload];
      vi.mocked(downloadsApi.retry).mockResolvedValue({});

      await state.retryDownload("dl-1");

      expect(state.downloadQueue[0].status).toBe("pending");
      expect(state.downloadQueue[0].error).toBeUndefined();
    });

    it("should call API to retry", async () => {
      state.downloadQueue = [mockDownload];
      vi.mocked(downloadsApi.retry).mockResolvedValue({});

      await state.retryDownload("dl-1");

      expect(downloadsApi.retry).toHaveBeenCalledWith("dl-1");
    });
  });

  describe("fetchDownloads", () => {
    it("should fetch and set downloads from API", async () => {
      const mockDownloads: Download[] = [mockDownload];
      vi.mocked(downloadsApi.getAll).mockResolvedValue(mockDownloads);

      await state.fetchDownloads();

      expect(state.downloadQueue).toEqual(mockDownloads);
    });

    it("should handle API errors gracefully", async () => {
      vi.mocked(downloadsApi.getAll).mockRejectedValue(
        new Error("Network error"),
      );
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      await state.fetchDownloads();

      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });
});
