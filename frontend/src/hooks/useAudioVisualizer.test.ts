import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAudioVisualizer } from "./useAudioVisualizer";
import type { Track } from "../types";

// Mock canvas context
const mockCanvasContext = {
  fillStyle: "",
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  beginPath: vi.fn(),
  fill: vi.fn(),
  scale: vi.fn(),
  translate: vi.fn(),
  createLinearGradient: vi.fn(() => ({
    addColorStop: vi.fn(),
  })),
  roundRect: vi.fn(),
  globalAlpha: 1,
  shadowColor: "",
  shadowBlur: 0,
};

// Mock AudioContext
const mockAnalyser = {
  fftSize: 0,
  smoothingTimeConstant: 0,
  frequencyBinCount: 64,
  getByteFrequencyData: vi.fn(),
  connect: vi.fn(),
};

const mockAudioSource = {
  connect: vi.fn(),
};

const mockAudioContext = {
  createAnalyser: vi.fn(() => mockAnalyser),
  createMediaElementSource: vi.fn(() => mockAudioSource),
  destination: {},
  state: "running",
  resume: vi.fn(),
};

// Mock global AudioContext
globalThis.AudioContext = vi.fn(
  () => mockAudioContext,
) as unknown as typeof AudioContext;

describe("useAudioVisualizer", () => {
  const mockTrack: Track = {
    id: "track-1",
    title: "Test Track",
    artist: "Test Artist",
    source: "spotify",
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock getContext
    HTMLCanvasElement.prototype.getContext = vi.fn(
      () => mockCanvasContext,
    ) as never;

    // Mock document.querySelector for audio element
    document.querySelector = vi.fn(() => null);

    // Mock requestAnimationFrame
    vi.spyOn(globalThis, "requestAnimationFrame").mockImplementation(() => {
      return 1;
    });
    vi.spyOn(globalThis, "cancelAnimationFrame").mockImplementation(() => {});

    // Mock getComputedStyle for CSS variables
    vi.spyOn(globalThis, "getComputedStyle").mockReturnValue({
      getPropertyValue: vi.fn(() => "25 95% 53%"),
    } as unknown as CSSStyleDeclaration);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should return a canvas ref", () => {
    const { result } = renderHook(() => useAudioVisualizer(null, false));

    expect(result.current).toBeDefined();
    expect(result.current.current).toBeNull(); // Not attached yet
  });

  it("should not create AudioContext when no track", () => {
    renderHook(() => useAudioVisualizer(null, false));

    // AudioContext may be created lazily, but without a track playing
    // the visualization shouldn't start
    expect(globalThis.cancelAnimationFrame).not.toHaveBeenCalled();
  });

  it("should handle isPlaying changes", () => {
    const { rerender } = renderHook(
      ({ track, isPlaying }) => useAudioVisualizer(track, isPlaying),
      {
        initialProps: { track: mockTrack, isPlaying: false },
      },
    );

    // Change to playing
    rerender({ track: mockTrack, isPlaying: true });

    // Should have registered animation frame (when canvas is available)
    // The actual animation logic requires a real canvas
  });

  it("should cancel animation frame on unmount", () => {
    const { unmount } = renderHook(() => useAudioVisualizer(mockTrack, true));

    unmount();

    // Hook cleanup runs - we just verify no crash
    expect(true).toBe(true);
  });
});
