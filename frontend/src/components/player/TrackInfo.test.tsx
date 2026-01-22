import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { Track } from "../../types";
import { TrackInfo } from "./TrackInfo";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("TrackInfo", () => {
  const mockTrack: Track = {
    id: "track-1",
    title: "Test Song Title",
    artist: "Test Artist Name",
    artist_id: "artist-1",
    source: "spotify",
    cover: "https://example.com/cover.jpg",
  };

  it("should render track title", () => {
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={false} />
      </MemoryRouter>
    );

    expect(screen.getByText("Test Song Title")).toBeTruthy();
  });

  it("should render track artist", () => {
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={false} />
      </MemoryRouter>
    );

    expect(screen.getByText("Test Artist Name")).toBeTruthy();
  });

  it("should render cover image when available", () => {
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={false} />
      </MemoryRouter>
    );

    const img = screen.getByAltText("Test Song Title");
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe("https://example.com/cover.jpg");
  });

  it("should render fallback emoji when no cover", () => {
    const trackWithoutCover = { ...mockTrack, cover: undefined };
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={trackWithoutCover} isExpanded={false} />
      </MemoryRouter>
    );

    expect(screen.getByText("🎵")).toBeTruthy();
  });

  it("should apply expanded styles when isExpanded is true", () => {
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={true} />
      </MemoryRouter>
    );

    // Title should have larger text in expanded mode
    const title = screen.getByText("Test Song Title");
    expect(title).toHaveClass("text-3xl");
  });

  it("should apply collapsed styles when isExpanded is false", () => {
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={false} />
      </MemoryRouter>
    );

    const title = screen.getByText("Test Song Title");
    expect(title).toHaveClass("text-sm");
  });

  it("should show larger cover in expanded mode", () => {
    const { container } = render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={true} />
      </MemoryRouter>
    );

    // Cover container should have expanded size classes
    const coverContainer = container.querySelector(".w-64");
    expect(coverContainer).toBeTruthy();
  });

  it("should show smaller cover in collapsed mode", () => {
    const { container } = render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={false} />
      </MemoryRouter>
    );

    const coverContainer = container.querySelector(".w-10");
    expect(coverContainer).toBeTruthy();
  });

  it("should handle long titles with truncation", () => {
    const longTitleTrack = {
      ...mockTrack,
      title: "This is a very long song title that should be truncated",
    };
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={longTitleTrack} isExpanded={false} />
      </MemoryRouter>
    );

    const title = screen.getByText(longTitleTrack.title);
    expect(title).toHaveClass("truncate");
  });

  it("should navigate to artist profile on click", () => {
    render(
      <MemoryRouter>
        <TrackInfo currentTrack={mockTrack} isExpanded={false} />
      </MemoryRouter>
    );

    const artistLink = screen.getByText("Test Artist Name");
    fireEvent.click(artistLink);
    expect(mockNavigate).toHaveBeenCalledWith("/artist/artist-1");
  });
});
