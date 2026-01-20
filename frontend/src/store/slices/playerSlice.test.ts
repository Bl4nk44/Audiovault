import { describe, it, expect, beforeEach, vi } from "vitest";
import { createPlayerSlice, type PlayerSlice } from "./playerSlice";

// localStorage is mocked globally in setupTests.ts
const localStorageMock = globalThis.localStorage as any;

describe("playerSlice", () => {
  let state: PlayerSlice;
  let set: (
    partial:
      | Partial<PlayerSlice>
      | ((state: PlayerSlice) => Partial<PlayerSlice>),
  ) => void;
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

  describe("pauseTrack", () => {
    it("should pause the current track", () => {
      state.isPlaying = true;

      state.pauseTrack();

      expect(state.isPlaying).toBe(false);
    });
  });

  describe("resumeTrack", () => {
    it("should resume the current track", () => {
      state.isPlaying = false;

      state.resumeTrack();

      expect(state.isPlaying).toBe(true);
    });
  });

  describe("seek", () => {
    it("should update current time", () => {
      state.seek(42);

      expect(state.currentTime).toBe(42);
    });
  });

  describe("updatePlaybackRate", () => {
    it("should update playback rate", () => {
      state.updatePlaybackRate(1.5);

      expect(state.playbackRate).toBe(1.5);
    });
  });

  describe("setVolume", () => {
    it("should set volume", () => {
      state.setVolume(0.8);

      expect(state.volume).toBe(0.8);
    });

    it("should persist volume to localStorage", () => {
      state.setVolume(0.6);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "player_volume",
        "0.6",
      );
    });
  });
});
