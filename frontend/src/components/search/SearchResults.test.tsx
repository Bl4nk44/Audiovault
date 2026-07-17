import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SearchResults from "./SearchResults";

// Mock dependencies
vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
// Mock child cards to avoid deep rendering complexity
vi.mock("./TrackCard", () => ({
  default: ({ track }: any) => <div data-testid="track-card">{track.title}</div>,
}));
vi.mock("./ArtistCard", () => ({
  default: ({ artist }: any) => <div data-testid="artist-card">{artist.title}</div>,
}));
vi.mock("./PlaylistCard", () => ({
  default: ({ playlist }: any) => <div data-testid="playlist-card">{playlist.title}</div>,
}));
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className }: any) => <div className={className}>{children}</div>,
  },
}));

describe("SearchResults Component", () => {
  it("renders loading skeletons", () => {
    render(<SearchResults results={[]} isLoading={true} />);
    // 10 skeletons rendered
    const skeletons = screen
      .getAllByRole("generic")
      .filter((el) => el.className.includes("animate-pulse"));
    expect(skeletons).toHaveLength(10);
  });

  it("renders empty state", () => {
    render(<SearchResults results={[]} isLoading={false} />);
    expect(screen.getByText("search.noResults")).toBeInTheDocument();
  });

  it("renders categorized results", () => {
    const results = [
      { id: "1", title: "Song 1", type: "track" },
      { id: "2", title: "Artist 1", type: "artist" },
      { id: "3", title: "Playlist 1", type: "playlist" },
    ] as any;

    render(<SearchResults results={results} isLoading={false} />);

    expect(screen.getByText("search.headers.tracks")).toBeInTheDocument();
    expect(screen.getByText("Song 1")).toBeInTheDocument();

    expect(screen.getByText("search.headers.artists")).toBeInTheDocument();
    expect(screen.getByText("Artist 1")).toBeInTheDocument();

    expect(screen.getByText("search.headers.playlists")).toBeInTheDocument();
    expect(screen.getByText("Playlist 1")).toBeInTheDocument();
  });

  it("renders track list in a single column on mobile", () => {
    const results = [{ id: "1", title: "Song 1", type: "track" }] as any;

    render(<SearchResults results={results} isLoading={false} />);

    const grid = screen.getByTestId("track-card").parentElement!;
    expect(grid.className).toContain("grid-cols-1");
    expect(grid.className).toContain("md:grid-cols-2");
  });

  it("renders loading skeletons matching the track row layout", () => {
    render(<SearchResults results={[]} isLoading={true} />);
    const skeletons = screen
      .getAllByRole("generic")
      .filter((el) => el.className.includes("animate-pulse"));
    const grid = skeletons[0].parentElement!;
    expect(grid.className).toContain("grid-cols-1");
    expect(grid.className).toContain("md:grid-cols-2");
    expect(skeletons[0].className).toContain("h-20");
  });
});
