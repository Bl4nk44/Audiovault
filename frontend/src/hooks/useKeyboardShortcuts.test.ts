import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useKeyboardShortcuts } from "./useKeyboardShortcuts";

// Mock store
const mockTogglePlay = vi.fn();
const mockNextTrack = vi.fn();
const mockPrevTrack = vi.fn();
const mockSetVolume = vi.fn();

vi.mock("../store/useStore", () => ({
  useStore: () => ({
    togglePlay: mockTogglePlay,
    nextTrack: mockNextTrack,
    prevTrack: mockPrevTrack,
    setVolume: mockSetVolume,
    volume: 0.5,
    currentTrack: { id: "1", title: "Test" },
  }),
}));

// Mock react-hotkeys-hook
const mockUseHotkeys = vi.fn();
vi.mock("react-hotkeys-hook", () => ({
  useHotkeys: (keys: string, callback: any) => mockUseHotkeys(keys, callback),
}));

describe("useKeyboardShortcuts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should register all shortcuts", () => {
    renderHook(() => useKeyboardShortcuts());

    // Check if useHotkeys was called for each shortcut group
    expect(mockUseHotkeys).toHaveBeenCalledWith("space", expect.any(Function));
    expect(mockUseHotkeys).toHaveBeenCalledWith("right", expect.any(Function));
    expect(mockUseHotkeys).toHaveBeenCalledWith("left", expect.any(Function));
    expect(mockUseHotkeys).toHaveBeenCalledWith("up, shift+=, =", expect.any(Function));
    expect(mockUseHotkeys).toHaveBeenCalledWith("down, -", expect.any(Function));
    expect(mockUseHotkeys).toHaveBeenCalledWith("m", expect.any(Function));
  });

  it("should trigger togglePlay on space", () => {
    renderHook(() => useKeyboardShortcuts());

    // Find the callback for 'space'
    const call = mockUseHotkeys.mock.calls.find((call) => call[0] === "space");
    const callback = call?.[1];

    // Simulate event
    const mockEvent = { preventDefault: vi.fn() };
    callback(mockEvent);

    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(mockTogglePlay).toHaveBeenCalled();
  });

  it("should trigger nextTrack on right arrow", () => {
    renderHook(() => useKeyboardShortcuts());
    const callback = mockUseHotkeys.mock.calls.find((call) => call[0] === "right")?.[1];
    callback({ preventDefault: vi.fn() });
    expect(mockNextTrack).toHaveBeenCalled();
  });

  it("should trigger prevTrack on left arrow", () => {
    renderHook(() => useKeyboardShortcuts());
    const callback = mockUseHotkeys.mock.calls.find((call) => call[0] === "left")?.[1];
    callback({ preventDefault: vi.fn() });
    expect(mockPrevTrack).toHaveBeenCalled();
  });

  it("should increase volume on up arrow", () => {
    renderHook(() => useKeyboardShortcuts());
    const callback = mockUseHotkeys.mock.calls.find((call) => call[0].includes("up"))?.[1];

    callback({ preventDefault: vi.fn() });

    // Volume was 0.5, should be 0.6
    expect(mockSetVolume).toHaveBeenCalledWith(0.6);
  });

  it("should decrease volume on down arrow", () => {
    renderHook(() => useKeyboardShortcuts());
    const callback = mockUseHotkeys.mock.calls.find((call) => call[0].includes("down"))?.[1];

    callback({ preventDefault: vi.fn() });

    // Volume was 0.5, should be 0.4
    expect(mockSetVolume).toHaveBeenCalledWith(0.4);
  });

  it("should mute/unmute on m", () => {
    renderHook(() => useKeyboardShortcuts());
    const callback = mockUseHotkeys.mock.calls.find((call) => call[0] === "m")?.[1];

    callback({ preventDefault: vi.fn() });

    // Volume was 0.5 (>0), so should set to 0
    expect(mockSetVolume).toHaveBeenCalledWith(0);
  });
});
