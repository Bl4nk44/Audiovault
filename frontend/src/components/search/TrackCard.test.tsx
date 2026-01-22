import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Track } from "../../types";
import TrackCard from "./TrackCard";

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", () => ({
  motion: {
    div: (props: any) => (
      <div {...props} data-testid={props.onClick ? "track-card" : undefined}>
        {props.children}
      </div>
    ),
    button: (props: any) => <button {...props}>{props.children}</button>,
  },
}));

// Mock the store
const { mockPlayTrack } = vi.hoisted(() => ({
  mockPlayTrack: vi.fn(),
}));

vi.mock("../../store/useStore", () => ({
  useStore: () => ({
    playTrack: mockPlayTrack,
    currentTrack: null,
    isPlaying: false,
    togglePlay: vi.fn(),
  }),
}));

// Mock API
const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
}));

vi.mock("../../services/api", () => ({
  default: {
    post: postMock,
  },
}));

// Mock notify
vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock AddToPlaylistModal
vi.mock("../AddToPlaylistModal", () => ({
  default: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="add-to-playlist-modal">Modal Open</div> : null,
}));

import { notify } from "../../utils/notify";

describe("TrackCard", () => {
  const mockTrack: Track = {
    id: "track-1",
    title: "Test Song",
    artist: "Test Artist",
    source: "spotify",
    duration_ms: 180000,
    cover: "https://example.com/cover.jpg",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    postMock.mockReset();
  });

  it("should render track title", () => {
    render(<TrackCard track={mockTrack} />);
    expect(screen.getByText("Test Song")).toBeTruthy();
  });

  it("should render track artist", () => {
    render(<TrackCard track={mockTrack} />);
    expect(screen.getByText("Test Artist")).toBeTruthy();
  });

  it("should render cover image when available", () => {
    render(<TrackCard track={mockTrack} />);
    const img = screen.getByAltText("Test Song");
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe("https://example.com/cover.jpg");
  });

  it("should format duration correctly", () => {
    render(<TrackCard track={mockTrack} />);
    expect(screen.getByText("3:00")).toBeTruthy();
  });

  it("should add to download queue when download button is clicked", async () => {
    postMock.mockResolvedValue({ data: {} });

    render(<TrackCard track={mockTrack} />);

    // JSDOM doesn't handle Tailwind visibility, so buttons are technically accessible to FireEvent
    // even if opacity-0 class is present.
    const downloadButton = screen.getByTitle("Download");
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith("/downloads/add", {
        track_id: "track-1",
        source: "spotify",
      });
      expect(notify.success).toHaveBeenCalledWith("Added to download queue");
    });
  });

  it("should show error when download fails", async () => {
    postMock.mockRejectedValue(new Error("Failed"));

    render(<TrackCard track={mockTrack} />);

    const downloadButton = screen.getByTitle("Download");
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to add to queue");
    });
  });

  it("should open playlist modal when add button is clicked", () => {
    render(<TrackCard track={mockTrack} />);

    const addButton = screen.getByTitle("Add to Playlist");
    fireEvent.click(addButton);

    expect(screen.getByTestId("add-to-playlist-modal")).toBeTruthy();
  });
});
