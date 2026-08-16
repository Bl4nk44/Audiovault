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

      expect(state.volume).toBeCloseTo(0.8);
    });
  });

  describe("queue management", () => {
    it("should add track to queue", () => {
      const track = { id: "1", title: "Test Track" } as any;
      state.addToQueue(track);
      expect(state.queue).toContainEqual(track);
    });
  });

  describe("playback navigation", () => {
    const track1 = { id: "1", title: "T1" } as any;
    const track2 = { id: "2", title: "T2" } as any;
    const track3 = { id: "3", title: "T3" } as any;
    const queue = [track1, track2, track3];

    beforeEach(() => {
      state.playTrack(track1, queue);
    });

    it("should skip to next track", () => {
      // playTrack sets index 0 for track1
      state.nextTrack();
      expect(state.currentTrackIndex).toBe(1);
      expect(state.currentTrack).toEqual(track2);
    });

    it("should not skip next if at end of queue", () => {
      state.playTrack(track3, queue); // index 2
      state.nextTrack();
      expect(state.currentTrackIndex).toBe(2);
      expect(state.currentTrack).toEqual(track3);
    });

    it("should skip to previous track", () => {
      state.playTrack(track2, queue); // index 1
      state.prevTrack();
      expect(state.currentTrackIndex).toBe(0);
      expect(state.currentTrack).toEqual(track1);
    });

    it("should not skip prev if at start of queue", () => {
      state.playTrack(track1, queue); // index 0
      state.prevTrack();
      expect(state.currentTrackIndex).toBe(0);
      expect(state.currentTrack).toEqual(track1);
    });
  });

  describe("visualizer mode", () => {
    it("should set visualizer mode", () => {
      expect(state.visualizerMode).toBe("classic");
      state.setVisualizerMode("mirror");
      expect(state.visualizerMode).toBe("mirror");
    });
  });
});
