import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RecommendationCard from "./RecommendationCard";
import { BrowserRouter } from "react-router-dom";
import type { RecommendedTrack } from "../../types/lastfm";

// Mocks
vi.mock("../AddToPlaylistModal", () => ({
  default: ({ isOpen, onClose, trackIds }: any) => 
    isOpen ? <div data-testid="playlist-modal">Modal {trackIds[0]} <button onClick={onClose}>Close</button></div> : null
}));

describe("RecommendationCard", () => {
  const mockTrack: RecommendedTrack = {
    name: "Test Song",
    artist: "Test Artist",
    image_url: "http://example.com/image.jpg",
    match: 0.95,
    url: "http://last.fm/test",
    mbid: "test-mbid",
    score: 100,
    playcount: 10,
    reason: "Similar Artist"
  };

  const mockOnPlay = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderCard = (track = mockTrack) => {
    return render(
      <BrowserRouter>
        <RecommendationCard track={track} onPlay={mockOnPlay} />
      </BrowserRouter>
    );
  };

  it("renders track info correctly", () => {
    renderCard();
    expect(screen.getByText("Test Song")).toBeInTheDocument();
    expect(screen.getByText("Test Artist")).toBeInTheDocument();
    expect(screen.getByText("95% Match")).toBeInTheDocument();
    const img = screen.getByAltText("Test Song");
    expect(img).toHaveAttribute("src", "http://example.com/image.jpg");
  });

  it("renders placeholder when image is missing", () => {
    renderCard({ ...mockTrack, image_url: null });
    expect(screen.getByText("T")).toBeInTheDocument(); // First letter of name
  });

  it("calls onPlay when play button is clicked", () => {
    renderCard();
    const playButton = screen.getByTitle(/^Play$/);
    fireEvent.click(playButton);
    expect(mockOnPlay).toHaveBeenCalledWith(mockTrack);
  });

  it("opens playlist modal when add button is clicked", () => {
    renderCard();
    const addButton = screen.getByTitle(/Add to playlist/i);
    fireEvent.click(addButton);
    
    expect(screen.getByTestId("playlist-modal")).toBeInTheDocument();
    expect(screen.getByText(/external:Test Artist:Test Song/)).toBeInTheDocument();
  });

  it("closes playlist modal when onClose is called", () => {
    renderCard();
    const addButton = screen.getByTitle(/Add to playlist/i);
    fireEvent.click(addButton);
    
    const closeButton = screen.getByText("Close");
    fireEvent.click(closeButton);
    
    expect(screen.queryByTestId("playlist-modal")).not.toBeInTheDocument();
  });
});
