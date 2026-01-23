import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TrackInfo } from "./TrackInfo";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

describe("TrackInfo", () => {
  const mockTrack = {
    id: "t1",
    title: "Test Track",
    artist: "Test Artist",
    artist_id: "a1",
    cover: "test.jpg",
  } as any;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders track information correctly", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={false} />);
    expect(screen.getByText("Test Track")).toBeInTheDocument();
    expect(screen.getByText("Test Artist")).toBeInTheDocument();
  });

  it("navigates to artist profile on click", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={false} />);
    fireEvent.click(screen.getByText("Test Artist"));
    expect(mockNavigate).toHaveBeenCalledWith("/artist/a1");
  });

  it("handles image error by showing placeholder", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={false} />);
    const img = screen.getByAltText("Test Track");
    fireEvent.error(img);
    expect(screen.getByText("🎵")).toBeInTheDocument();
  });

  it("renders expanded view", () => {
    render(<TrackInfo currentTrack={mockTrack} isExpanded={true} />);
    const h3 = screen.getByText("Test Track");
    expect(h3).toHaveClass("text-3xl");
  });
});
