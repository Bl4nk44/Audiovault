import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LyricsPanel from "./LyricsPanel";

// Mock store
const mockCurrentTrack = {
  id: "1",
  title: "Test Song",
  artist: "Test Artist",
};

vi.mock("../../store/useStore", () => ({
  useStore: () => ({
    currentTrack: mockCurrentTrack,
  }),
}));

// Mock API
const mockSearchLyrics = vi.fn();
vi.mock("../../api/lyrics", () => ({
  lyricsApi: {
    search: (artist: string, title: string) => mockSearchLyrics(artist, title),
  },
}));

// Query Client for tests
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe("LyricsPanel", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  const renderComponent = (isOpen = true) => {
    render(
      <QueryClientProvider client={queryClient}>
        <LyricsPanel isOpen={isOpen} onClose={vi.fn()} currentTime={0} />
      </QueryClientProvider>
    );
  };

  it("should not render when isOpen is false", () => {
    renderComponent(false);
    expect(screen.queryByText("Lyrics")).not.toBeInTheDocument();
  });

  it("should render and show loading state", () => {
    // Return a promise that doesn't resolve immediately to test loading state
    mockSearchLyrics.mockImplementation(() => new Promise(() => {}));

    renderComponent(true);

    expect(screen.getByText("Lyrics")).toBeInTheDocument();
    expect(screen.getByText("Test Song")).toBeInTheDocument();
    expect(screen.getByText("Fetching lyrics...")).toBeInTheDocument();
  });

  it("should display lyrics when found", async () => {
    mockSearchLyrics.mockResolvedValue({
      found: true,
      lyrics: "These are the lyrics",
      url: "http://example.com/lyrics",
    });

    renderComponent(true);

    await waitFor(() => {
      expect(screen.getByText("These are the lyrics")).toBeInTheDocument();
    });
    expect(screen.getByText("View on Genius")).toBeInTheDocument();
  });

  it("should display not found message", async () => {
    mockSearchLyrics.mockResolvedValue({
      found: false,
      lyrics: null,
    });

    renderComponent(true);

    await waitFor(() => {
      expect(screen.getByText("No lyrics found for this song")).toBeInTheDocument();
    });
  });

  it("should display error state", async () => {
    mockSearchLyrics.mockRejectedValue(new Error("Network error"));

    renderComponent(true);

    await waitFor(
      () => {
        expect(screen.getByText("Failed to load lyrics")).toBeInTheDocument();
      },
      { timeout: 4000 }
    );
  });
});
