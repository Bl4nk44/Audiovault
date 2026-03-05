import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RecommendationsPage from "./RecommendationsPage";
import { BrowserRouter } from "react-router-dom";
import * as lastfmService from "../services/lastfm";
import api from "../services/api";
import { toast } from "react-hot-toast";

// Mocks
vi.mock("../services/lastfm", () => ({
  getLastfmStatus: vi.fn(),
  getRecommendations: vi.fn(),
  connectLastfm: vi.fn(),
  disconnectLastfm: vi.fn(),
  callbackLastfm: vi.fn(),
}));

vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}));

// Mock sub-components to stay focused on RecommendationsPage logic
vi.mock("../components/dashboard/ArtistRecommendationCard", () => ({
  default: () => <div data-testid="artist-card" />,
}));
vi.mock("../components/dashboard/LastfmProfileCard", () => ({
  default: ({ username }: { username: string }) => <div data-testid="profile-card">{username}</div>,
}));
vi.mock("../components/dashboard/PlaylistRecommendationCard", () => ({
  default: () => <div data-testid="playlist-card" />,
}));
vi.mock("../components/dashboard/RecommendationCard", () => ({
  default: ({ track, onPlay }: any) => (
    <div data-testid="track-card">
      <span>{track.name}</span>
      <button onClick={() => onPlay(track)}>Play</button>
    </div>
  ),
}));

const mockNavigate = vi.fn();
const mockSearchParams = new URLSearchParams();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [mockSearchParams],
  };
});

// Mock i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback,
  }),
}));

describe("RecommendationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams.delete("token");
  });

  const renderPage = () => {
    return render(
      <BrowserRouter>
        <RecommendationsPage />
      </BrowserRouter>
    );
  };

  it("renders connect button when not connected", async () => {
    vi.mocked(lastfmService.getLastfmStatus).mockResolvedValue({ connected: false, username: null });
    renderPage();

    await waitFor(() => {
      // There's a button "Connect Last.fm" and a header "Connect Last.fm to get started"
      expect(screen.getAllByText(/Connect Last.fm/i)).toHaveLength(2);
    });
  });

  it("handles Last.fm callback when token is present in URL", async () => {
    mockSearchParams.set("token", "test-token");
    vi.mocked(lastfmService.getLastfmStatus).mockResolvedValue({ connected: false, username: null });
    vi.mocked(lastfmService.callbackLastfm).mockResolvedValue({ status: "success" } as any);

    renderPage();

    await waitFor(() => {
      expect(lastfmService.callbackLastfm).toHaveBeenCalledWith("test-token");
      expect(toast.success).toHaveBeenCalledWith("Successfully connected to Last.fm!");
      expect(mockNavigate).toHaveBeenCalledWith("/recommendations", { replace: true });
    });
  });

  it("renders recommendations when connected", async () => {
    vi.mocked(lastfmService.getLastfmStatus).mockResolvedValue({ connected: true, username: "testuser" });
    vi.mocked(lastfmService.getRecommendations).mockResolvedValue({
      source: "lastfm",
      cache_status: "hit",
      lastfm_connected: true,
      generated_at: new Date().toISOString(),
      tracks: [{ name: "Song 1", artist: "Artist 1" } as any],
      artists: [],
      playlists: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("profile-card")).toHaveTextContent("testuser");
      expect(screen.getByTestId("track-card")).toBeInTheDocument();
      expect(screen.getByText("Song 1")).toBeInTheDocument();
    });
  });

  it("handles tab switching", async () => {
    vi.mocked(lastfmService.getLastfmStatus).mockResolvedValue({ connected: true, username: "testuser" });
    vi.mocked(lastfmService.getRecommendations).mockResolvedValue({
      source: "lastfm",
      cache_status: "hit",
      lastfm_connected: true,
      generated_at: new Date().toISOString(),
      tracks: [],
      artists: [{ name: "Artist A" } as any],
      playlists: [{ id: "pl1", name: "List A" } as any],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/No track recommendations found/i)).toBeInTheDocument();
    });

    // Switch to Artists - use exact match to avoid "Playlist" button
    fireEvent.click(screen.getByRole("button", { name: /^Artists$/i }));
    await waitFor(() => {
      expect(screen.getByTestId("artist-card")).toBeInTheDocument();
    });

    // Switch to Playlists
    fireEvent.click(screen.getByRole("button", { name: /^Playlists$/i }));
    await waitFor(() => {
      expect(screen.getByTestId("playlist-card")).toBeInTheDocument();
    });
  });

  it("handles track play action", async () => {
    vi.mocked(lastfmService.getLastfmStatus).mockResolvedValue({ connected: true, username: "testuser" });
    vi.mocked(lastfmService.getRecommendations).mockResolvedValue({
      source: "lastfm",
      cache_status: "hit",
      lastfm_connected: true,
      generated_at: new Date().toISOString(),
      tracks: [{ name: "Recommended", artist: "Cool Artist" } as any],
      artists: [],
      playlists: [],
    });
    
    // Mock search API
    vi.mocked(api.get).mockResolvedValue({
      data: [{ id: "track-123", name: "Recommended", artist: "Cool Artist", source: "deezer" }],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("track-card")).toBeInTheDocument();
    });

    // Use exact name match for the "Play" button in the track card
    fireEvent.click(screen.getByRole("button", { name: /^Play$/i }));

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/browse/search", expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith("Playing Recommended");
    });
  });

  it("handles disconnect", async () => {
    vi.mocked(lastfmService.getLastfmStatus).mockResolvedValue({ connected: true, username: "testuser" });
    vi.mocked(lastfmService.getRecommendations).mockResolvedValue({
      source: "lastfm",
      cache_status: "hit",
      lastfm_connected: true,
      generated_at: new Date().toISOString(),
      tracks: [],
      artists: [],
      playlists: [],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Disconnect/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Disconnect/i));

    await waitFor(() => {
      expect(lastfmService.disconnectLastfm).toHaveBeenCalled();
      expect(lastfmService.getLastfmStatus).toHaveBeenCalledTimes(2); // Initial + after disconnect
    });
  });
});
