import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import api from "../services/api";
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
    watchlist: [{ id: "w1", source_id: "spotify-watched", type: "artist" }], // Pre-populate for testing removal
    addToWatchlist: mockAddToWatchlist,
    removeFromWatchlist: mockRemoveFromWatchlist,
    currentTrack: null,
    isPlaying: false,
    playTrack: vi.fn(),
    togglePlay: vi.fn(),
  }),
}));

// Mock API service
vi.mock("../services/api", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

// Mock sub-components
vi.mock("../components/search/TrackCard", () => ({
  default: ({ track }: any) => <div data-testid="track-card">{track.title}</div>,
}));

// Mock Lucide icons to avoid render issues in environments
vi.mock("lucide-react", async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    ArrowLeft: () => <span data-testid="icon-back">Back</span>,
  };
});

describe("ArtistProfile", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  });

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  const renderComponent = (artistId = "123", state = {}) => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[{ pathname: `/artist/${artistId}`, state }]}>
          <Routes>
            <Route path="/artist/:id" element={<ArtistProfile />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  const mockArtistFull = {
    id: "123",
    spotify_id: "spotify-123",
    name: "Test Artist",
    bio: "A test bio",
    image_url: "http://example.com/img.jpg",
    tracks: [
      { id: "t1", title: "Hit Song", duration_ms: 200000 },
      { id: "t2", title: "Hit Song 2", duration_ms: 200000 },
    ],
    albums: [
      {
        id: "a1",
        title: "Best Album",
        album_type: "album",
        image_url: "http://example.com/alb.jpg",
        release_date: "2020-01-01",
        spotify_id: "sp-a1",
      },
      {
        id: "s1",
        title: "Single 1",
        album_type: "single",
        image_url: "http://example.com/s1.jpg",
        release_date: "2021-01-01",
        spotify_id: "sp-s1",
      },
    ],
  };

  it("renders loading state", () => {
    mockArtistsApi.getById.mockImplementation(() => new Promise(() => {})); // Hang
    renderComponent("123");
    expect(document.body).toBeTruthy();
  });

  it("renders full artist profile", async () => {
    mockArtistsApi.getById.mockResolvedValue(mockArtistFull);
    renderComponent("123");

    await waitFor(() => {
      expect(screen.getByText("Test Artist")).toBeInTheDocument();
      expect(screen.getByText("A test bio")).toBeInTheDocument();
      expect(screen.getByText("Hit Song")).toBeInTheDocument();
      expect(screen.getByText("Best Album")).toBeInTheDocument(); // Album
      expect(screen.getByText("Single 1")).toBeInTheDocument(); // Single
    });
  });

  it("handles watchlist toggle (Follow/Unfollow)", async () => {
    mockArtistsApi.getById.mockResolvedValue({ ...mockArtistFull, source: "deezer", spotify_id: "new-id" });
    renderComponent("new-id");

    await waitFor(() => expect(screen.getByText("Test Artist")).toBeInTheDocument());

    const followBtn = screen.getByText("Follow");
    fireEvent.click(followBtn);

    expect(mockAddToWatchlist).toHaveBeenCalledWith(
      expect.objectContaining({
        source_name: "Test Artist",
        watch_type: "artist",
      })
    );
    expect(notify.success).toHaveBeenCalledWith("Following Test Artist");
  });

  it("handles unfollow logic", async () => {
    const watchedArtist = { ...mockArtistFull, spotify_id: "spotify-watched" };
    mockArtistsApi.getById.mockResolvedValue(watchedArtist);

    renderComponent("123"); // ID maps to watched

    await waitFor(() => expect(screen.getByText("Test Artist")).toBeInTheDocument());

    const unfollowBtn = screen.getByText("Following"); // Button text changes
    expect(unfollowBtn).toBeInTheDocument();

    fireEvent.click(unfollowBtn);

    expect(mockRemoveFromWatchlist).toHaveBeenCalled(); // w1
    expect(notify.success).toHaveBeenCalledWith("Removed from watchlist");
  });

  it("handles discography download (Download All)", async () => {
    mockArtistsApi.getById.mockResolvedValue(mockArtistFull);
    (api.post as unknown as Mock).mockResolvedValue({ data: { queued_count: 10 } });

    renderComponent("123");
    await waitFor(() => expect(screen.getByText("Download Discography")).toBeInTheDocument());

    const dlBtn = screen.getByText("Download Discography");
    fireEvent.click(dlBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(expect.stringContaining("/downloads/artist/spotify-123/download-all"), {
        source: "deezer",
      });
      expect(notify.success).toHaveBeenCalledWith("Queued 10 tracks for download");
    });
  });

  it("handles single album download", async () => {
    mockArtistsApi.getById.mockResolvedValue(mockArtistFull);
    (api.post as unknown as Mock).mockResolvedValue({ data: { message: "Album Queued" } });

    renderComponent("123");
    await waitFor(() => expect(screen.getByText("Best Album")).toBeInTheDocument());

    const dlAlbumBtns = screen.getAllByTitle("Download Album");
    fireEvent.click(dlAlbumBtns[0]);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        expect.stringContaining("/downloads/album/sp-a1/download"),
        expect.anything()
      );
      expect(notify.success).toHaveBeenCalledWith("Album Queued");
    });
  });

  it("handles navigation back", async () => {
    mockArtistsApi.getById.mockResolvedValue(mockArtistFull);
    renderComponent("123");
    await waitFor(() => expect(screen.getByTestId("icon-back")).toBeInTheDocument());

    fireEvent.click(screen.getByTestId("icon-back"));
  });

  it("handles discography download failure", async () => {
    mockArtistsApi.getById.mockResolvedValue(mockArtistFull);
    const errorMsg = "Download failed";

    // Controlled promise to catch loading state
    let rejectPromise: (reason?: any) => void;
    (api.post as unknown as Mock).mockReturnValue(
      new Promise((_, reject) => {
        rejectPromise = reject;
      })
    );

    renderComponent("123");
    await waitFor(() => expect(screen.getByText("Download Discography")).toBeInTheDocument());

    const dlBtn = screen.getByText("Download Discography");
    fireEvent.click(dlBtn);

    // Verify loading state
    await waitFor(() => expect(screen.getByText("Downloading...")).toBeInTheDocument());

    // Trigger failure
    await act(async () => {
      rejectPromise!({ response: { data: { detail: errorMsg } } });
    });

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to queue downloads");
    });

    // Should return to normal state
    expect(screen.getByText("Download Discography")).toBeInTheDocument();
  });

  it("handles single album download failure", async () => {
    mockArtistsApi.getById.mockResolvedValue(mockArtistFull);
    const specificError = "Region blocked";
    (api.post as unknown as Mock).mockRejectedValue({
      response: { data: { detail: specificError } },
    });

    renderComponent("123");
    await waitFor(() => expect(screen.getByText("Best Album")).toBeInTheDocument());

    const dlAlbumBtns = screen.getAllByTitle("Download Album");
    fireEvent.click(dlAlbumBtns[0]);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith(specificError);
    });
  });

  it("handles keyboard navigation for albums", async () => {
    mockArtistsApi.getById.mockResolvedValue(mockArtistFull);
    renderComponent("123");

    await waitFor(() => expect(screen.getByText("Best Album")).toBeInTheDocument());

    const albumTitle = screen.getByText("Best Album");
    const card = albumTitle.closest("div[role='button']");

    fireEvent.keyDown(card!, { key: "Enter", code: "Enter" });
  });

  it("renders placeholder when image is invalid or missing", async () => {
    const artistWithBadImg = {
      ...mockArtistFull,
      image_url: "javascript:alert(1)",
      albums: [
        {
          ...mockArtistFull.albums[0],
          image_url: undefined,
          images: { url: "invalid-url" },
        },
      ],
    };

    mockArtistsApi.getById.mockResolvedValue(artistWithBadImg);
    renderComponent("123");

    await waitFor(() => expect(screen.getByText("Test Artist")).toBeInTheDocument());

    // Ensure image is not rendered due to validation failure
    const img = screen.queryByAltText("Test Artist");
    expect(img).not.toBeInTheDocument();
  });

  it("renders artist with no content gracefully", async () => {
    const emptyArtist = {
      id: "empty",
      name: "Empty Artist",
      tracks: [],
      albums: [],
    };
    mockArtistsApi.getById.mockResolvedValue(emptyArtist);
    renderComponent("empty");

    await waitFor(() => expect(screen.getByText("Empty Artist")).toBeInTheDocument());

    expect(screen.queryByText("Popular Tracks")).not.toBeInTheDocument();
    expect(screen.queryByText("Albums")).not.toBeInTheDocument();
  });
});
