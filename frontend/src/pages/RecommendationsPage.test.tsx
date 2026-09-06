import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RecommendationsPage from "./RecommendationsPage";
import { BrowserRouter } from "react-router-dom";
import * as lastfmService from "../services/lastfm";
import * as listeningService from "../services/listening";
import api from "../services/api";
import { toast } from "react-hot-toast";

vi.mock("../services/lastfm", () => ({
  getRecommendations: vi.fn(),
  callbackLastfm: vi.fn(),
}));

vi.mock("../services/listening", () => ({
  getProviders: vi.fn(),
  connectRedirectProvider: vi.fn(),
  connectTokenProvider: vi.fn(),
  disconnectProvider: vi.fn(),
  setListeningPreference: vi.fn(),
}));

vi.mock("../services/api", () => ({ default: { get: vi.fn() } }));

vi.mock("react-hot-toast", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}));

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

vi.mock("../hooks/useTranslation", () => ({
  useTranslation: () => ({
    t: (_key: string, fallback: string) => fallback,
    language: "en",
  }),
}));

const providersResponse = (over: {
  lastfmConnected?: boolean;
  lbConnected?: boolean;
  preference?: string;
} = {}) => ({
  preference: over.preference ?? "auto",
  providers: [
    {
      name: "lastfm",
      display_name: "Last.fm",
      connected: over.lastfmConnected ?? false,
      username: over.lastfmConnected ? "lfuser" : null,
      supports_recommendations: true,
      connects_with_token: false,
    },
    {
      name: "listenbrainz",
      display_name: "ListenBrainz",
      connected: over.lbConnected ?? false,
      username: over.lbConnected ? "lbuser" : null,
      supports_recommendations: true,
      connects_with_token: true,
    },
  ],
});

const emptyRecs = {
  source: "lastfm+deezer",
  cache_status: "hit",
  provider: "lastfm",
  lastfm_connected: true,
  generated_at: new Date().toISOString(),
  tracks: [],
  artists: [],
  playlists: [],
};

describe("RecommendationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams.delete("token");
  });

  const renderPage = () =>
    render(
      <BrowserRouter>
        <RecommendationsPage />
      </BrowserRouter>
    );

  it("shows connect controls for both providers when nothing is connected", async () => {
    vi.mocked(listeningService.getProviders).mockResolvedValue(providersResponse());
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Connect Last\.fm/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Connect ListenBrainz/i })).toBeInTheDocument();
      expect(screen.getByText(/Connect a listening service to get started/i)).toBeInTheDocument();
    });
  });

  it("handles the Last.fm redirect callback from ?token=", async () => {
    mockSearchParams.set("token", "test-token");
    vi.mocked(listeningService.getProviders).mockResolvedValue(providersResponse());
    vi.mocked(lastfmService.callbackLastfm).mockResolvedValue(undefined);

    renderPage();

    await waitFor(() => {
      expect(lastfmService.callbackLastfm).toHaveBeenCalledWith("test-token");
      expect(toast.success).toHaveBeenCalledWith("Successfully connected to Last.fm!");
      expect(mockNavigate).toHaveBeenCalledWith("/recommendations", { replace: true });
    });
  });

  it("connects ListenBrainz with a pasted token", async () => {
    vi.mocked(listeningService.getProviders).mockResolvedValue(providersResponse());
    vi.mocked(listeningService.connectTokenProvider).mockResolvedValue({ username: "lbuser" });

    renderPage();

    const input = await screen.findByPlaceholderText(/Paste your token/i);
    fireEvent.change(input, { target: { value: "  my-lb-token  " } });
    fireEvent.click(screen.getByRole("button", { name: /Connect ListenBrainz/i }));

    await waitFor(() => {
      expect(listeningService.connectTokenProvider).toHaveBeenCalledWith("listenbrainz", "my-lb-token");
    });
  });

  it("renders recommendations and the Last.fm profile card when connected", async () => {
    vi.mocked(listeningService.getProviders).mockResolvedValue(
      providersResponse({ lastfmConnected: true })
    );
    vi.mocked(lastfmService.getRecommendations).mockResolvedValue({
      ...emptyRecs,
      tracks: [{ name: "Song 1", artist: "Artist 1" }],

    } as any);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("profile-card")).toHaveTextContent("lfuser");
      expect(screen.getByText("Song 1")).toBeInTheDocument();
    });
  });

  it("shows a recommendation-source switch when both providers are connected", async () => {
    vi.mocked(listeningService.getProviders).mockResolvedValue(
      providersResponse({ lastfmConnected: true, lbConnected: true })
    );

    vi.mocked(lastfmService.getRecommendations).mockResolvedValue(emptyRecs as any);
    vi.mocked(listeningService.setListeningPreference).mockResolvedValue(undefined);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Recommendation source/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^ListenBrainz$/i }));
    await waitFor(() => {
      expect(listeningService.setListeningPreference).toHaveBeenCalledWith("listenbrainz");
    });
  });

  it("switches tabs", async () => {
    vi.mocked(listeningService.getProviders).mockResolvedValue(
      providersResponse({ lastfmConnected: true })
    );
    vi.mocked(lastfmService.getRecommendations).mockResolvedValue({
      ...emptyRecs,
      artists: [{ name: "Artist A" }],
      playlists: [{ id: "pl1", title: "List A" }],

    } as any);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/No track recommendations found/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^artists$/i }));
    await waitFor(() => expect(screen.getByTestId("artist-card")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^playlists$/i }));
    await waitFor(() => expect(screen.getByTestId("playlist-card")).toBeInTheDocument());
  });

  it("plays a recommended track via browse search", async () => {
    vi.mocked(listeningService.getProviders).mockResolvedValue(
      providersResponse({ lastfmConnected: true })
    );
    vi.mocked(lastfmService.getRecommendations).mockResolvedValue({
      ...emptyRecs,
      tracks: [{ name: "Recommended", artist: "Cool Artist" }],

    } as any);
    vi.mocked(api.get).mockResolvedValue({
      data: [{ id: "track-123", name: "Recommended", artist: "Cool Artist", source: "deezer" }],
    });

    renderPage();
    await waitFor(() => expect(screen.getByTestId("track-card")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^Play$/i }));

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/browse/search", expect.any(Object));
      expect(toast.success).toHaveBeenCalledWith("Playing Recommended");
    });
  });

  it("disconnects a provider and reloads", async () => {
    vi.mocked(listeningService.getProviders).mockResolvedValue(
      providersResponse({ lastfmConnected: true })
    );

    vi.mocked(lastfmService.getRecommendations).mockResolvedValue(emptyRecs as any);
    vi.mocked(listeningService.disconnectProvider).mockResolvedValue(undefined);

    renderPage();
    await waitFor(() => expect(screen.getByText(/Disconnect/i)).toBeInTheDocument());

    fireEvent.click(screen.getByText(/Disconnect/i));

    await waitFor(() => {
      expect(listeningService.disconnectProvider).toHaveBeenCalledWith("lastfm");
      expect(listeningService.getProviders).toHaveBeenCalledTimes(2);
    });
  });
});
