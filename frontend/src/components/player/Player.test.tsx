/* eslint-disable */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAudioVisualizer } from "../../hooks/useAudioVisualizer";
import { useStore } from "../../store/useStore";
import Player from "./Player";

// 1. Mock dependencies
vi.mock("../../store/useStore");
vi.mock("../../hooks/useAudioVisualizer", () => ({
  useAudioVisualizer: vi.fn(),
}));
vi.mock("../../services/api", () => ({
  default: {
    post: vi.fn().mockResolvedValue({}),
  },
}));

// 2. Mock child components
vi.mock("./PlayerControls", () => ({
  PlayerControls: ({ togglePlay, isPlaying }: any) => (
    <div data-testid="controls">
      <button onClick={togglePlay}>{isPlaying ? "Pause" : "Play"}</button>
    </div>
  ),
}));
vi.mock("./ProgressBar", () => ({
  ProgressBar: ({ onSeek, currentTime }: any) => (
    <div data-testid="progress">
      <span data-testid="time">{Math.round(currentTime)}</span>
      <button onClick={() => onSeek(50)}>Seek 50</button>
    </div>
  ),
}));
vi.mock("./TrackInfo", () => ({
  TrackInfo: ({ currentTrack }: any) => <div data-testid="track-info">{currentTrack?.title}</div>,
}));
vi.mock("./VolumeControl", () => ({
  VolumeControl: ({ setVolume }: any) => (
    <button onClick={() => setVolume(0.5)} data-testid="volume">
      Set Volume
    </button>
  ),
}));
vi.mock("./VisualizerToggle", () => ({
  VisualizerToggle: ({ showVisualizer, setShowVisualizer }: any) => (
    <div data-testid="vis-toggle" onClick={() => setShowVisualizer(!showVisualizer)}>
      Toggle
    </div>
  ),
}));
vi.mock("./LyricsPanel", () => ({
  default: ({ isOpen, onClose }: any) =>
    isOpen ? (
      <div data-testid="lyrics-panel">
        Lyrics
        <button onClick={onClose}>Close Lyrics</button>
      </div>
    ) : null,
}));

// 3. Mock Framer Motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className, ...props }: any) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
  },
}));

describe("Player Component - Deep Dive", () => {
  const mockTrack = {
    id: "1",
    title: "Bohemian Rhapsody",
    artist: "Queen",
    album: "A Night at the Opera",
    duration: 354,
    filename: "queen/bohemian.mp3",
    cover: "cover.jpg",
  };

  const mockActions = {
    togglePlay: vi.fn(),
    setVolume: vi.fn(),
    nextTrack: vi.fn(),
    prevTrack: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useAudioVisualizer as any).mockReturnValue({ current: null });

    // Polyfill MediaMetadata
    // @ts-ignore
    globalThis.MediaMetadata = class MediaMetadata {
      title: string;
      artist: string;
      album: string;
      artwork: any[];
      constructor(init: any) {
        this.title = init.title;
        this.artist = init.artist;
        this.album = init.album;
        this.artwork = init.artwork;
      }
    };

    // Mock global navigator mediaSession
    Object.defineProperty(navigator, "mediaSession", {
      writable: true,
      value: {
        metadata: null,
        setActionHandler: vi.fn(),
      },
    });

    // Mock HTMLMediaElement methods
    vi.spyOn(window.HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
    vi.spyOn(window.HTMLMediaElement.prototype, "pause").mockImplementation(() => {});

    // Reset store default return
    (useStore as unknown as Mock).mockReturnValue({
      currentTrack: mockTrack,
      isPlaying: false,
      volume: 1.0,
      visualizerMode: "classic",
      ...mockActions,
    });
  });

  it("renders correctly with full track data", () => {
    render(<Player />);
    expect(screen.getByTestId("track-info")).toHaveTextContent("Bohemian Rhapsody");
  });

  it("handles seek commands", async () => {
    const { container } = render(<Player />);
    const audio = container.querySelector("audio") as HTMLAudioElement;

    fireEvent.click(screen.getByText("Seek 50"));
    expect(audio.currentTime).toBe(50);
    await waitFor(() => {
      expect(screen.getByTestId("time")).toHaveTextContent("50");
    });
  });

  it("opens and closes lyrics panel", () => {
    render(<Player />);
    fireEvent.click(screen.getByTitle("Lyrics"));
    expect(screen.getByTestId("lyrics-panel")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Close Lyrics"));
    expect(screen.queryByTestId("lyrics-panel")).not.toBeInTheDocument();
  });

  it("toggles visualizer", () => {
    render(<Player />);
    // Initial state: showVisualizer is true
    expect(useAudioVisualizer).toHaveBeenCalledWith(
      expect.anything(),
      false, // showVisualizer is true but isPlaying is false -> should be false
      expect.anything(),
      "classic"
    );

    fireEvent.click(screen.getByTestId("vis-toggle"));
  });

  it("handles media session action: seekto", async () => {
    render(<Player />);
    const seekToHandler = (navigator.mediaSession.setActionHandler as Mock).mock.calls.find(
      (call) => call[0] === "seekto"
    )?.[1];

    const audio = document.querySelector("audio") as HTMLAudioElement;
    act(() => {
      seekToHandler({ seekTime: 120 });
    });

    expect(audio.currentTime).toBe(120);
    await waitFor(() => {
      expect(screen.getByTestId("time")).toHaveTextContent("120");
    });
  });

  it("handles stream URL construction for tracks without filenames", () => {
    const trackNoFile = { ...mockTrack, filename: undefined };
    (useStore as unknown as Mock).mockReturnValue({
      currentTrack: trackNoFile,
      isPlaying: false,
      volume: 1.0,
      ...mockActions,
    });

    const { container } = render(<Player />);
    const audio = container.querySelector("audio") as HTMLAudioElement;
    expect(audio.src).toContain("/stream/1.mp3");
  });

  it("null check: should not render if no track", () => {
    (useStore as unknown as Mock).mockReturnValue({
      currentTrack: null,
      isPlaying: false,
      ...mockActions,
    });
    const { container } = render(<Player />);
    expect(container.firstChild).toBeNull();
  });
});
