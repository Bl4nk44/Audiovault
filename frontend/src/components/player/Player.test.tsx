import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Player from "./Player";

// Mock sub-components
vi.mock("./PlayerControls", () => ({
  PlayerControls: () => <div data-testid="player-controls">Controls</div>,
}));
vi.mock("./ProgressBar", () => ({
  ProgressBar: () => <div data-testid="progress-bar">Progress</div>,
}));
vi.mock("./TrackInfo", () => ({
  TrackInfo: () => <div data-testid="track-info">Track Info</div>,
}));
vi.mock("./VolumeControl", () => ({
  VolumeControl: () => <div data-testid="volume-control">Volume</div>,
}));
vi.mock("./LyricsPanel", () => ({
  default: () => <div data-testid="lyrics-panel">Lyrics Panel</div>,
}));
vi.mock("./VisualizerToggle", () => ({
  VisualizerToggle: () => <div data-testid="visualizer-toggle">Vis Toggle</div>,
}));

// Hoisted mocks for dynamic overriding
const { mockUseStore, mockUseAudioVisualizer } = vi.hoisted(() => ({
  mockUseStore: vi.fn(),
  mockUseAudioVisualizer: vi.fn(),
}));

// Mock hooks
vi.mock("../../store/useStore", () => ({
  useStore: mockUseStore,
}));

vi.mock("../../hooks/useAudioVisualizer", () => ({
  useAudioVisualizer: mockUseAudioVisualizer,
}));

// Mock services
vi.mock("../../services/api", () => ({
  default: {
    post: vi.fn().mockResolvedValue({}),
  },
}));

describe("Player", () => {
  const defaultStoreState = {
    currentTrack: { id: "1", title: "Test", filename: "test.mp3" },
    isPlaying: false,
    togglePlay: vi.fn(),
    volume: 0.5,
    setVolume: vi.fn(),
    nextTrack: vi.fn(),
    prevTrack: vi.fn(),
    visualizerMode: "bar",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseStore.mockReturnValue(defaultStoreState);
    mockUseAudioVisualizer.mockReturnValue({ current: null });

    // Mock HTMLMediaElement
    window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
    window.HTMLMediaElement.prototype.pause = vi.fn();
  });

  it("should render player components when track is playing", () => {
    render(<Player />);

    expect(screen.getByTestId("player-controls")).toBeInTheDocument();
    expect(screen.getByTestId("progress-bar")).toBeInTheDocument();
    expect(screen.getByTestId("track-info")).toBeInTheDocument();
    expect(screen.getByTestId("volume-control")).toBeInTheDocument();
  });

  it("should render audio element with correct src", () => {
    render(<Player />);
    const audio = document.querySelector("audio");
    expect(audio).toBeInTheDocument();
    expect(audio?.src).toContain("/stream/test.mp3");
  });

  it("should not render if no current track", () => {
    // Override store for this test
    mockUseStore.mockReturnValue({
      ...defaultStoreState,
      currentTrack: null,
    });

    const { container } = render(<Player />);
    expect(container).toBeEmptyDOMElement();
  });
});
