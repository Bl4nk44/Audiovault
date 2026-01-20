import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrackInfo } from "./TrackInfo";
import type { Track } from "../../types";

describe("TrackInfo", () => {
  const mockTrack: Track = {
    id: "track-1",
    title: "Test Song Title",
    artist: "Test Artist Name",
    source: "spotify",
    cover: "https://example.com/cover.jpg",
  };

  it("should render track title", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={false} />);

    expect(screen.getByText("Test Song Title")).toBeTruthy();
  });

  it("should render track artist", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={false} />);

    expect(screen.getByText("Test Artist Name")).toBeTruthy();
  });

  it("should render cover image when available", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={false} />);

    const img = screen.getByAltText("Test Song Title");
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe("https://example.com/cover.jpg");
  });

  it("should render fallback emoji when no cover", () => {
    const trackWithoutCover = { ...mockTrack, cover: undefined };
    render(<TrackInfo currentTrack={trackWithoutCover} isExpanded={false} />);

    expect(screen.getByText("🎵")).toBeTruthy();
  });

  it("should apply expanded styles when isExpanded is true", () => {
    const { container } = render(
      <TrackInfo currentTrack={mockTrack} isExpanded={true} />,
    );

    // Title should have larger text in expanded mode
    const title = screen.getByText("Test Song Title");
    expect(title).toHaveClass("text-3xl");
  });

  it("should apply collapsed styles when isExpanded is false", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={false} />);

    const title = screen.getByText("Test Song Title");
    expect(title).toHaveClass("text-sm");
  });

  it("should show larger cover in expanded mode", () => {
    const { container } = render(
      <TrackInfo currentTrack={mockTrack} isExpanded={true} />,
    );

    // Cover container should have expanded size classes
    const coverContainer = container.querySelector(".w-64");
    expect(coverContainer).toBeTruthy();
  });

  it("should show smaller cover in collapsed mode", () => {
    const { container } = render(
      <TrackInfo currentTrack={mockTrack} isExpanded={false} />,
    );

    const coverContainer = container.querySelector(".w-10");
    expect(coverContainer).toBeTruthy();
  });

  it("should handle long titles with truncation", () => {
    const longTitleTrack = {
      ...mockTrack,
      title: "This is a very long song title that should be truncated",
    };
    render(<TrackInfo currentTrack={longTitleTrack} isExpanded={false} />);

    const title = screen.getByText(longTitleTrack.title);
    expect(title).toHaveClass("truncate");
  });
});
