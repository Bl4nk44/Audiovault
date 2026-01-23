import { useQuery } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStore } from "../store/useStore";
import AlbumDetails from "./AlbumDetails";

// Mock hooks
vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
}));

vi.mock("../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("../utils/notify", () => ({
  notify: { success: vi.fn(), error: vi.fn() },
}));

// Mock child components
vi.mock("../components/search/TrackCard", () => ({
  default: ({ track }: any) => <div data-testid="track-card">{track.title}</div>,
}));
vi.mock("../components/ui/Button", () => ({
  default: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
}));
vi.mock("../components/AddToPlaylistModal", () => ({
  default: ({ isOpen }: any) => (isOpen ? <div data-testid="playlist-modal">Modal</div> : null),
}));

describe("AlbumDetails Page", () => {
  const mockAlbum = {
    id: "123",
    title: "Test Album",
    artist: "Test Artist",
    album_type: "album",
    tracks: [
      { id: "t1", title: "Track 1", artist: "Test Artist", duration_ms: 60000 },
      { id: "t2", title: "Track 2", artist: "Test Artist", duration_ms: 120000 },
    ],
    image_url: "http://example.com/cover.jpg",
    total_tracks: 2,
    release_date: "2023-01-01",
  };

  const addToQueueMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as any).mockReturnValue({ addToQueue: addToQueueMock });
  });

  const renderWithRouter = (initialRoute = "/album/123") => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/album/:id" element={<AlbumDetails />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it("renders loading state", () => {
    (useQuery as any).mockReturnValue({ isLoading: true });
    renderWithRouter();
    expect(screen.queryByText("Failed to load album")).not.toBeInTheDocument();
  });

  it("renders error state", () => {
    (useQuery as any).mockReturnValue({ isLoading: false, error: true });
    renderWithRouter();
    expect(screen.getByText("Failed to load album")).toBeInTheDocument();
    expect(screen.getByText("Go Back")).toBeInTheDocument();
  });

  it("renders album details and tracks", async () => {
    (useQuery as any).mockReturnValue({ isLoading: false, data: mockAlbum });
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText("Test Album")).toBeInTheDocument();
    });

    expect(screen.getByText("Test Artist")).toBeInTheDocument();
    expect(screen.getByText("Album")).toBeInTheDocument();
    expect(screen.getByText("2023")).toBeInTheDocument();
    expect(screen.getByText("Track 1")).toBeInTheDocument();
  });

  it("handles download all", async () => {
    (useQuery as any).mockReturnValue({ isLoading: false, data: mockAlbum });
    renderWithRouter();

    await waitFor(() => screen.getByText("Download Album"));
    const downloadBtn = screen.getByText("Download Album");
    fireEvent.click(downloadBtn);

    expect(addToQueueMock).toHaveBeenCalledTimes(2);
    expect(addToQueueMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Track 1" }));
  });

  it("opens add to playlist modal", async () => {
    (useQuery as any).mockReturnValue({ isLoading: false, data: mockAlbum });
    renderWithRouter();

    await waitFor(() => screen.getByText("Test Album"));

    // Find button by text content partial match or exact
    // The button has icon then text.
    // We can use getByRole("button", { name: /Add to Playlist/i })
    // mocked button renders children directly.
    // so it should contain "Add to Playlist" text node.

    const playlistBtn = screen.getByRole("button", { name: /Add to Playlist/i });
    fireEvent.click(playlistBtn);

    expect(screen.getByTestId("playlist-modal")).toBeInTheDocument();
  });
});
