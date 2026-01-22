import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPlayerSlice, type PlayerSlice } from "./playerSlice";

// localStorage is mocked globally in setupTests.ts
const localStorageMock = globalThis.localStorage as any;

describe("playerSlice", () => {
  let state: PlayerSlice;
  let set: (partial: Partial<PlayerSlice> | ((state: PlayerSlice) => Partial<PlayerSlice>)) => void;
  let get: () => PlayerSlice;

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

    state = createPlayerSlice(set, get, {} as never);
  });

  describe("initial state", () => {
    it("should have null currentTrack", () => {
      expect(state.currentTrack).toBeNull();
    });

    it("should have empty queue", () => {
      expect(state.queue).toEqual([]);
    });

    it("should not be playing", () => {
      expect(state.isPlaying).toBe(false);
    });
  });

  describe("playTrack", () => {
    it("should set current track and start playing", () => {
      const track = { id: "1", title: "Test Track", duration: 180 } as any;

      state.playTrack(track);

      expect(state.currentTrack).toEqual(track);
      expect(state.isPlaying).toBe(true);
    });
  });

  describe("togglePlay", () => {
    it("should toggle playing state", () => {
      state.isPlaying = false;
      state.togglePlay();
      expect(state.isPlaying).toBe(true);

      state.togglePlay();
      expect(state.isPlaying).toBe(false);
    });
  });

  describe("setVolume", () => {
    it("should set volume", () => {
      state.setVolume(0.8);

      expect(state.volume).toBe(0.8);
    });
  });

  describe("queue management", () => {
    it("should add track to queue", () => {
      const track = { id: "1", title: "Test Track" } as any;
      state.addToQueue(track);
      expect(state.queue).toContainEqual(track);
    });
  });
});
