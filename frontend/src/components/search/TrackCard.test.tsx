import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TrackCard from "./TrackCard";
import type { Track } from "../../types";

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", () => ({
  motion: {
    div: ({
      children,
      onClick,
      className,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
      className?: string;
    }) => (
      <div onClick={onClick} className={className}>
        {children}
      </div>
    ),
    button: ({
      children,
      onClick,
      className,
      title,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
      className?: string;
      title?: string;
    }) => (
      <button onClick={onClick} className={className} title={title}>
        {children}
      </button>
    ),
  },
}));

// Mock the store
const mockPlayTrack = vi.fn();
vi.mock("../../store/useStore", () => ({
  useStore: () => ({
    playTrack: mockPlayTrack,
  }),
}));

// Mock API
vi.mock("../../services/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

// Mock notify
vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import api from "../../services/api";
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

  it("should render fallback when no cover image", () => {
    const trackWithoutCover = {
      ...mockTrack,
      cover: undefined,
      image_url: undefined,
    };
    render(<TrackCard track={trackWithoutCover} />);

    // Should render Music icon placeholder
    expect(screen.queryByAltText("Test Song")).toBeNull();
  });

  it("should format duration correctly", () => {
    render(<TrackCard track={mockTrack} />);

    // 180000ms = 3:00
    expect(screen.getByText("3:00")).toBeTruthy();
  });

  it("should call playTrack when card is clicked", async () => {
    const user = userEvent.setup();
    render(<TrackCard track={mockTrack} />);

    // Click on the card
    await user.click(screen.getByText("Test Song"));

    expect(mockPlayTrack).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "track-1",
        title: "Test Song",
        artist: "Test Artist",
      }),
      undefined,
    );
  });

  it("should add to download queue when download button is clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ data: {} });

    render(<TrackCard track={mockTrack} />);

    const downloadButton = screen.getByTitle("Download");
    await user.click(downloadButton);

    expect(api.post).toHaveBeenCalledWith("/downloads/add", {
      track_id: "track-1",
      source: "spotify",
    });
    expect(notify.success).toHaveBeenCalledWith("Added to download queue");
  });

  it("should show error when download fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockRejectedValue(new Error("Failed"));

    render(<TrackCard track={mockTrack} />);

    const downloadButton = screen.getByTitle("Download");
    await user.click(downloadButton);

    expect(notify.error).toHaveBeenCalledWith("Failed to add to queue");
  });

  it("should add to library when add button is clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ data: {} });

    render(<TrackCard track={mockTrack} />);

    const addButton = screen.getByTitle("Add to Library");
    await user.click(addButton);

    expect(api.post).toHaveBeenCalledWith(
      "/watchlist/add",
      expect.objectContaining({
        watch_type: "track",
        source: "spotify",
        source_id: "track-1",
      }),
    );
    expect(notify.success).toHaveBeenCalledWith("Added to library");
  });
});
