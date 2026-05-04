import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ArtistRecommendationCard from "./ArtistRecommendationCard";
import type { RecommendedArtist } from "../../types/lastfm";

describe("ArtistRecommendationCard", () => {
  const mockArtist: RecommendedArtist = {
    name: "Test Artist",
    url: "http://last.fm/artist",
    image_url: "http://example.com/artist.jpg",
    match: 0.85,
    tags: ["rock", "indie"],
    mbid: "test-mbid"
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderCard = (artist = mockArtist) => {
    return render(
      <MemoryRouter>
        <ArtistRecommendationCard artist={artist} />
      </MemoryRouter>
    );
  };

  it("renders artist info correctly", () => {
    renderCard();
    expect(screen.getByText("Test Artist")).toBeInTheDocument();
    expect(screen.getByText("85% Match")).toBeInTheDocument();
    const img = screen.getByAltText("Test Artist");
    expect(img).toHaveAttribute("src", "http://example.com/artist.jpg");
  });

  it("renders placeholder icon when image is missing", () => {
    renderCard({ ...mockArtist, image_url: null });
    // IoPerson is rendered as an SVG, we can't easily check for the component by name
    // but we can check if the img is NOT there
    expect(screen.queryByAltText("Test Artist")).not.toBeInTheDocument();
  });

  it("has a link to the artist profile", () => {
    renderCard();
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "http://last.fm/artist");
    expect(link).toHaveAttribute("target", "_blank");
  });
});
