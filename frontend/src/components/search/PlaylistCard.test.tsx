import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Playlist } from "../../types";
import PlaylistCard from "./PlaylistCard";

// Mock framer-motion
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
      <div onClick={onClick} className={className} data-testid="playlist-card">
        {children}
      </div>
    ),
    button: ({
      children,
      onClick,
      disabled,
      className,
      title,
    }: {
      children: React.ReactNode;
      onClick?: (e: React.MouseEvent) => void;
      disabled?: boolean;
      className?: string;
      title?: string;
    }) => (
      <button onClick={onClick} disabled={disabled} className={className} title={title}>
        {children}
      </button>
    ),
  },
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

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import api from "../../services/api";
import { notify } from "../../utils/notify";

describe("PlaylistCard", () => {
  const mockPlaylist: Playlist = {
    id: "playlist-1",
    name: "Test Playlist",
    title: "Test Playlist",
    source: "spotify",
    image_url: "https://example.com/playlist.jpg",
    tracks_count: 25,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderPlaylistCard = (playlist: Playlist = mockPlaylist) => {
    return render(
      <MemoryRouter>
        <PlaylistCard playlist={playlist} />
      </MemoryRouter>
    );
  };

  it.each([
    ["playlist title", "Test Playlist"],
    ["source", "spotify"],
    ["tracks count", "25 tracks"],
  ])("should render %s", (_label, text) => {
    renderPlaylistCard();

    expect(screen.getByText(text)).toBeTruthy();
  });

  it("should not render tracks count when not provided", () => {
    const playlistWithoutCount = { ...mockPlaylist, tracks_count: undefined };
    renderPlaylistCard(playlistWithoutCount);

    expect(screen.queryByText(/tracks/)).toBeNull();
  });

  it("should render playlist image when available", () => {
    renderPlaylistCard();

    const img = screen.getByAltText("Test Playlist");
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe("https://example.com/playlist.jpg");
  });

  it("should render fallback when no image", () => {
    const playlistWithoutImage = { ...mockPlaylist, image_url: undefined };
    renderPlaylistCard(playlistWithoutImage);

    expect(screen.queryByAltText("Test Playlist")).toBeNull();
  });

  it("should navigate to playlist page on click", async () => {
    const user = userEvent.setup();
    renderPlaylistCard();

    await user.click(screen.getByTestId("playlist-card"));

    expect(mockNavigate).toHaveBeenCalledWith("/playlist/playlist-1", {
      state: { source: "spotify" },
    });
  });

  it("should add to watchlist when button is clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    renderPlaylistCard();

    const addButton = screen.getByTitle("Add to Watchlist");
    await user.click(addButton);

    expect(api.post).toHaveBeenCalledWith(
      "/watchlist/add",
      expect.objectContaining({
        watch_type: "playlist",
        source: "spotify",
        source_id: "playlist-1",
        source_name: "Test Playlist",
        auto_download: true,
      })
    );
    expect(notify.success).toHaveBeenCalledWith("Playlist added to watchlist");
  });

  it("should show error when adding fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockRejectedValue(new Error("Failed"));
    renderPlaylistCard();

    const addButton = screen.getByTitle("Add to Watchlist");
    await user.click(addButton);

    expect(notify.error).toHaveBeenCalledWith("Failed to add to watchlist");
  });

  it("should render spotify icon for spotify source", () => {
    renderPlaylistCard();

    expect(screen.getByAltText("Spotify")).toBeTruthy();
  });

  it("should render youtube icon for youtube source", () => {
    const youtubePlaylist = { ...mockPlaylist, source: "youtube" };
    renderPlaylistCard(youtubePlaylist);

    expect(screen.getByAltText("YouTube")).toBeTruthy();
  });
});
