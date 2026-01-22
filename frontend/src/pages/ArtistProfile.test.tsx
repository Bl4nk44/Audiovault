import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { notify } from "../utils/notify";
import ArtistProfile from "./ArtistProfile";

// Mock dependencies
vi.mock("../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock artists API with hoisting
const { mockArtistsApi } = vi.hoisted(() => ({
  mockArtistsApi: {
    getById: vi.fn(),
  },
}));

vi.mock("../api/artists", () => ({
  artistsApi: mockArtistsApi,
}));

// Mock Store
const mockAddToWatchlist = vi.fn();
const mockRemoveFromWatchlist = vi.fn();

vi.mock("../store/useStore", () => ({
  useStore: () => ({
    watchlist: [],
    addToWatchlist: mockAddToWatchlist,
    removeFromWatchlist: mockRemoveFromWatchlist,
    currentTrack: null,
    isPlaying: false,
    playTrack: vi.fn(),
    togglePlay: vi.fn(),
  }),
}));

// Mock simple fetch
globalThis.fetch = vi.fn();

// Mock components
vi.mock("../components/search/TrackCard", () => ({
  default: () => <div data-testid="track-card">Track Card</div>,
}));

describe("ArtistProfile", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  const renderComponent = (artistId = "123") => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/artist/${artistId}`]}>
          <Routes>
            <Route path="/artist/:id" element={<ArtistProfile />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it("should handle album download using spotify_id if available", async () => {
    const mockArtist = {
      id: "local-id",
      name: "Test Artist",
      spotify_id: "spotify-artist-id",
      albums: [
        {
          id: "local-album-id",
          title: "Test Album",
          spotify_id: "spotify-album-id",
          album_type: "album",
          total_tracks: 10,
          images: { url: "cover.jpg" },
        },
      ],
      tracks: [],
    };

    mockArtistsApi.getById.mockResolvedValue(mockArtist);
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ message: "Queued" }),
    } as Response);

    renderComponent("local-id");

    // Wait for loading to finish
    await waitFor(() => expect(screen.getByText("Test Artist")).toBeTruthy());

    // Find download button for album and click
    const downloadButton = screen.getByTitle("Download Album");
    fireEvent.click(downloadButton);

    await waitFor(() => {
      // Should call with SPOTIFY ID
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/v1/downloads/album/spotify-album-id/download",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ source: "spotify" }),
        })
      );
      expect(notify.success).toHaveBeenCalledWith("Queued");
    });
  });

  it("should fallback to local id if spotify_id is missing", async () => {
    const mockArtist = {
      id: "local-id",
      name: "Test Artist",
      albums: [
        {
          id: "local-album-id",
          title: "Local Album",
          // spotify_id missing
          album_type: "album",
          total_tracks: 5,
        },
      ],
    };

    mockArtistsApi.getById.mockResolvedValue(mockArtist);
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ message: "Queued" }),
    } as Response);

    renderComponent("local-id");

    await waitFor(() => expect(screen.getByText("Test Artist")).toBeTruthy());

    const downloadButton = screen.getByTitle("Download Album");
    fireEvent.click(downloadButton);

    await waitFor(() => {
      // Should call with LOCAL ID
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/v1/downloads/album/local-album-id/download",
        expect.any(Object)
      );
    });
  });
});
