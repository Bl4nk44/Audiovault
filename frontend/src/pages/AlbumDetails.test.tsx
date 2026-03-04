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

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("AlbumDetails Page", () => {
  // ... existing describe setup ...
  // I need to be careful not to replace the whole describe block content if I can help it,
  // but sticking the mock before describe is fine.
  // And I'll append tests at the end.

  // Wait, I can't put the mock INSIDE describe if I use replace_file_content for the whole file or large chunks.
  // The mock needs to be top level.
  // And I need to append tests.
  // I will use two chunks. One for top level mock, one for appending tests.

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

  it("handles navigation to artist profile", async () => {
    (useQuery as any).mockReturnValue({
      isLoading: false,
      data: { ...mockAlbum, artist_id: "artist-123" },
    });
    renderWithRouter();

    await waitFor(() => screen.getByText("Test Artist"));
    fireEvent.click(screen.getByText("Test Artist"));

    expect(mockNavigate).toHaveBeenCalledWith(
      "/artist/artist-123",
      expect.objectContaining({ state: { source: "deezer" } })
    );
  });

  it("handles back navigation", () => {
    (useQuery as any).mockReturnValue({ isLoading: false, data: mockAlbum });
    renderWithRouter();

    fireEvent.click(screen.getByText("Back"));
    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it("renders placeholder when cover image is invalid or missing", async () => {
    // Assuming isValidImageUrl returns false for "invalid-url" based on previous context,
    // or we mock the util if we want to be strict.
    // However, AlbumDetails.tsx imports isValidImageUrl.
    // If isValidImageUrl("invalid-url") is false/true depends on implementation.
    // Let's assume empty string or null is definitely invalid.
    const albumEmptyImg = { ...mockAlbum, image_url: "" };

    (useQuery as any).mockReturnValue({ isLoading: false, data: albumEmptyImg });
    renderWithRouter();

    await waitFor(() => screen.getByText("Test Album"));
    const img = screen.queryByRole("img", { name: "Test Album" });
    expect(img).not.toBeInTheDocument();
    // It should render the Disc icon placeholder
    // Disc icon is usually an svg, hard to query by role strictly, but we can check if img is absent.
  });

  it("renders gracefully without release date", async () => {
    const albumNoDate = { ...mockAlbum, release_date: null };
    (useQuery as any).mockReturnValue({ isLoading: false, data: albumNoDate });
    renderWithRouter();

    await waitFor(() => screen.getByText("Test Album"));
    // Should verify it does not crash and maybe doesn't show "NaN" or similar
    expect(screen.getByText("Test Album")).toBeInTheDocument();
  });
});
