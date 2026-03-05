import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PlaylistRecommendationCard from "./PlaylistRecommendationCard";
import { BrowserRouter } from "react-router-dom";
import type { RecommendedPlaylist } from "../../types/lastfm";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("PlaylistRecommendationCard", () => {
  const mockPlaylist: RecommendedPlaylist = {
    id: "playlist-123",
    title: "Test Playlist",
    description: "Cool tracks",
    image_url: "http://example.com/playlist.jpg",
    track_count: 25,
    source: "spotify",
    url: "http://spotify.com/playlist"
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderCard = (playlist = mockPlaylist) => {
    return render(
      <BrowserRouter>
        <PlaylistRecommendationCard playlist={playlist} />
      </BrowserRouter>
    );
  };

  it("renders playlist info correctly", () => {
    renderCard();
    expect(screen.getByText("Test Playlist")).toBeInTheDocument();
    expect(screen.getByText(/25.*tracks/)).toBeInTheDocument();
    expect(screen.getByText(/spotify/i)).toBeInTheDocument();
    const img = screen.getByAltText("Test Playlist");
    expect(img).toHaveAttribute("src", "http://example.com/playlist.jpg");
  });

  it("navigates to playlist details on click", () => {
    renderCard();
    const card = screen.getByRole("button");
    fireEvent.click(card);
    expect(mockNavigate).toHaveBeenCalledWith("/playlist/playlist-123", { state: { source: "spotify" } });
  });

  it("navigates to playlist details on Enter key", () => {
    renderCard();
    const card = screen.getByRole("button");
    fireEvent.keyDown(card, { key: "Enter" });
    expect(mockNavigate).toHaveBeenCalledWith("/playlist/playlist-123", { state: { source: "spotify" } });
  });

  it("link plays the playlist externally", () => {
    renderCard();
    const playLink = screen.getByRole("link");
    expect(playLink).toHaveAttribute("href", "http://spotify.com/playlist");
    expect(playLink).toHaveAttribute("target", "_blank");
  });

  it("renders placeholder icon when image is missing", () => {
    renderCard({ ...mockPlaylist, image_url: null });
    expect(screen.queryByAltText("Test Playlist")).not.toBeInTheDocument();
  });
});
