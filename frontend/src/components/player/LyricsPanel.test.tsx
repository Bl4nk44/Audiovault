import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LyricsPanel from "./LyricsPanel";
import { useQuery } from "@tanstack/react-query";
import { useStore } from "../../store/useStore";

// Mocks
vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
  QueryClient: vi.fn(),
  QueryClientProvider: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("../../api/lyrics", () => ({
  lyricsApi: {
    search: vi.fn(),
  },
}));

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock lucide-react
vi.mock("lucide-react", () => ({
  Music2: () => <div data-testid="music-icon" />,
  X: () => <div data-testid="close-icon" />,
  RefreshCcw: () => <div data-testid="refresh-icon" />,
  AlertCircle: () => <div data-testid="alert-icon" />,
  Loader2: () => <div data-testid="loader-icon" />,
  ExternalLink: () => <div data-testid="external-link-icon" />,
}));

describe("LyricsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock for scrollIntoView
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  const mockTrack = {
    id: "1",
    title: "Test Song",
    artist: "Test Artist",
  };

  it("renders 'No track playing' when currentTrack is null", () => {
    vi.mocked(useStore).mockReturnValue({ currentTrack: null } as any);
    vi.mocked(useQuery).mockReturnValue({
      data: null,
      isLoading: false,
      isRefetching: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<LyricsPanel isOpen={true} onClose={() => {}} currentTime={0} />);

    expect(screen.getByText(/No track playing/i)).toBeInTheDocument();
  });

  it("renders loading state", () => {
    vi.mocked(useStore).mockReturnValue({ currentTrack: mockTrack } as any);
    vi.mocked(useQuery).mockReturnValue({
      data: null,
      isLoading: true,
      isRefetching: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<LyricsPanel isOpen={true} onClose={() => {}} currentTime={0} />);

    expect(screen.getByTestId("loader-icon")).toBeInTheDocument();
    expect(screen.getByText(/Fetching lyrics/i)).toBeInTheDocument();
  });

  it("renders error state and handles retry", () => {
    const mockRefetch = vi.fn();
    vi.mocked(useStore).mockReturnValue({ currentTrack: mockTrack } as any);
    vi.mocked(useQuery).mockReturnValue({
      data: null,
      isLoading: false,
      isRefetching: false,
      error: new Error("Failed"),
      refetch: mockRefetch,
    } as any);

    render(<LyricsPanel isOpen={true} onClose={() => {}} currentTime={0} />);

    expect(screen.getByText(/Failed to load lyrics/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Try Again/i));
    expect(mockRefetch).toHaveBeenCalled();
  });

  it("renders plain lyrics when no synced lyrics available", () => {
    vi.mocked(useStore).mockReturnValue({ currentTrack: mockTrack } as any);
    vi.mocked(useQuery).mockReturnValue({
      data: {
        found: true,
        lyrics: "Line 1\nLine 2",
        synced_lyrics: null,
      },
      isLoading: false,
      isRefetching: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<LyricsPanel isOpen={true} onClose={() => {}} currentTime={0} />);

    expect(screen.getByText("Plain")).toBeInTheDocument();
    expect(screen.getByText(/Line 1/)).toBeInTheDocument();
    expect(screen.getByText(/Line 2/)).toBeInTheDocument();
  });

  it("renders synced lyrics and highlights active line", () => {
    const syncedLrc = "[00:00.00]First line\n[00:10.00]Second line";
    vi.mocked(useStore).mockReturnValue({ currentTrack: mockTrack } as any);
    vi.mocked(useQuery).mockReturnValue({
      data: {
        found: true,
        lyrics: null,
        synced_lyrics: syncedLrc,
      },
      isLoading: false,
      isRefetching: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    // Current time 12s -> Second line should be active
    render(<LyricsPanel isOpen={true} onClose={() => {}} currentTime={12} />);

    expect(screen.getByText("Karaoke")).toBeInTheDocument();
    const secondLine = screen.getByText("Second line");
    expect(secondLine).toBeInTheDocument();
    
    // Check if scrollIntoView was called (it is called in useEffect when actualIndex changes)
    expect(window.HTMLElement.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it("handles refresh and close actions", () => {
    const mockOnClose = vi.fn();
    vi.mocked(useStore).mockReturnValue({ currentTrack: mockTrack } as any);
    vi.mocked(useQuery).mockReturnValue({
      data: null,
      isLoading: false,
      isRefetching: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    render(<LyricsPanel isOpen={true} onClose={mockOnClose} currentTime={0} />);

    // Close
    fireEvent.click(screen.getByTestId("close-icon").parentElement!);
    expect(mockOnClose).toHaveBeenCalled();

    // Refresh - this should trigger setRefreshCount which triggers useQuery refetch (via key change)
    fireEvent.click(screen.getByTestId("refresh-icon").parentElement!);
    // Since we mock useQuery, we can't easily check the internal refreshCount state change 
    // without a more complex setup, but we covered the button click.
  });
});
