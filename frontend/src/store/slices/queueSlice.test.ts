import { describe, it, expect, beforeEach, vi } from "vitest";
import { createQueueSlice, type QueueSlice } from "./queueSlice";

// localStorage is mocked globally in setupTests.ts
const localStorageMock = globalThis.localStorage as any;

describe("queueSlice", () => {
  let state: QueueSlice;
  let set: (
    partial: Partial<QueueSlice> | ((state: QueueSlice) => Partial<QueueSlice>),
  ) => void;
  let get: () => QueueSlice;

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

    state = createQueueSlice(set, get, {} as never);
  });

  describe("initial state", () => {
    it("should have empty queue", () => {
      expect(state.queue).toEqual([]);
    });

    it("should have current index -1", () => {
      expect(state.currentIndex).toBe(-1);
    });

    it("should have shuffle disabled", () => {
      expect(state.isShuffle).toBe(false);
    });
  });

  describe("addToQueue", () => {
    it("should add track to queue", () => {
      const track = { id: "1", title: "Track 1" } as any;

      state.addToQueue(track);

      expect(state.queue).toContainEqual(track);
    });
  });

  describe("removeFromQueue", () => {
    it("should remove track from queue", () => {
      const track = { id: "1", title: "Track 1" } as any;
      state.queue = [track];

      state.removeFromQueue(0);

      expect(state.queue).toEqual([]);
    });
  });

  describe("clearQueue", () => {
    it("should clear the queue", () => {
      state.queue = [
        { id: "1", title: "Track 1" } as any,
        { id: "2", title: "Track 2" } as any,
      ];

      state.clearQueue();

      expect(state.queue).toEqual([]);
      expect(state.currentIndex).toBe(-1);
    });
  });

  describe("nextTrack", () => {
    it("should move to next track", () => {
      state.queue = [
        { id: "1", title: "Track 1" } as any,
        { id: "2", title: "Track 2" } as any,
      ];
      state.currentIndex = 0;

      state.nextTrack();

      expect(state.currentIndex).toBe(1);
    });
  });

  describe("previousTrack", () => {
    it("should move to previous track", () => {
      state.queue = [
        { id: "1", title: "Track 1" } as any,
        { id: "2", title: "Track 2" } as any,
      ];
      state.currentIndex = 1;

      state.previousTrack();

      expect(state.currentIndex).toBe(0);
    });
  });

  describe("toggleShuffle", () => {
    it("should toggle shuffle mode", () => {
      state.isShuffle = false;

      state.toggleShuffle();

      expect(state.isShuffle).toBe(true);
    });
  });
});
