import { describe, it, expect, beforeEach } from "vitest";
import { createPlayerSlice, type PlayerSlice } from "./playerSlice";
import type { Track } from "../../types";

describe("playerSlice", () => {
  let state: PlayerSlice;
  let set: (
    partial:
      | Partial<PlayerSlice>
      | ((state: PlayerSlice) => Partial<PlayerSlice>),
  ) => void;
  let get: () => PlayerSlice;

  const mockTrack: Track = {
    id: "track-1",
    title: "Test Track",
    artist: "Test Artist",
    source: "spotify",
    duration_ms: 180000,
  };

  const mockTrack2: Track = {
    id: "track-2",
    title: "Another Track",
    artist: "Another Artist",
    source: "youtube",
    duration_ms: 240000,
  };

  const mockQueue: Track[] = [mockTrack, mockTrack2];

  beforeEach(() => {
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

    it("should not be playing", () => {
      expect(state.isPlaying).toBe(false);
    });

    it("should have volume of 1", () => {
      expect(state.volume).toBe(1);
    });

    it("should have empty queue", () => {
      expect(state.queue).toEqual([]);
    });

    it("should have currentTrackIndex of -1", () => {
      expect(state.currentTrackIndex).toBe(-1);
    });
  });

  describe("playTrack", () => {
    it("should set current track and start playing", () => {
      state.playTrack(mockTrack);

      expect(state.currentTrack).toEqual(mockTrack);
      expect(state.isPlaying).toBe(true);
    });

    it("should set queue to single track when no queue provided", () => {
      state.playTrack(mockTrack);

      expect(state.queue).toEqual([mockTrack]);
      expect(state.currentTrackIndex).toBe(0);
    });

    it("should set queue when provided", () => {
      state.playTrack(mockTrack, mockQueue);

      expect(state.queue).toEqual(mockQueue);
      expect(state.currentTrackIndex).toBe(0);
    });

    it("should find correct index in queue", () => {
      state.playTrack(mockTrack2, mockQueue);

      expect(state.currentTrackIndex).toBe(1);
    });
  });

  describe("togglePlay", () => {
    it("should toggle isPlaying from false to true", () => {
      expect(state.isPlaying).toBe(false);

      state.togglePlay();

      expect(state.isPlaying).toBe(true);
    });

    it("should toggle isPlaying from true to false", () => {
      state.playTrack(mockTrack);
      expect(state.isPlaying).toBe(true);

      state.togglePlay();

      expect(state.isPlaying).toBe(false);
    });
  });

  describe("setVolume", () => {
    it("should set volume to specified value", () => {
      state.setVolume(0.5);

      expect(state.volume).toBe(0.5);
    });

    it("should allow volume of 0", () => {
      state.setVolume(0);

      expect(state.volume).toBe(0);
    });

    it("should allow volume of 1", () => {
      state.setVolume(1);

      expect(state.volume).toBe(1);
    });
  });

  describe("nextTrack", () => {
    it("should move to next track in queue", () => {
      state.playTrack(mockTrack, mockQueue);
      expect(state.currentTrackIndex).toBe(0);

      state.nextTrack();

      expect(state.currentTrack).toEqual(mockTrack2);
      expect(state.currentTrackIndex).toBe(1);
      expect(state.isPlaying).toBe(true);
    });

    it("should not change track if at end of queue", () => {
      state.playTrack(mockTrack2, mockQueue);
      expect(state.currentTrackIndex).toBe(1);

      state.nextTrack();

      expect(state.currentTrack).toEqual(mockTrack2);
      expect(state.currentTrackIndex).toBe(1);
    });
  });

  describe("prevTrack", () => {
    it("should move to previous track in queue", () => {
      state.playTrack(mockTrack, mockQueue);
      state.nextTrack();
      expect(state.currentTrackIndex).toBe(1);

      state.prevTrack();

      expect(state.currentTrack).toEqual(mockTrack);
      expect(state.currentTrackIndex).toBe(0);
      expect(state.isPlaying).toBe(true);
    });

    it("should not change track if at beginning of queue", () => {
      state.playTrack(mockTrack, mockQueue);
      expect(state.currentTrackIndex).toBe(0);

      state.prevTrack();

      expect(state.currentTrack).toEqual(mockTrack);
      expect(state.currentTrackIndex).toBe(0);
    });
  });

  describe("addToQueue", () => {
    it("should add track to end of queue", () => {
      state.playTrack(mockTrack);
      expect(state.queue).toHaveLength(1);

      state.addToQueue(mockTrack2);

      expect(state.queue).toHaveLength(2);
      expect(state.queue[1]).toEqual(mockTrack2);
    });

    it("should add track to empty queue", () => {
      state.addToQueue(mockTrack);

      expect(state.queue).toEqual([mockTrack]);
    });
  });
});
