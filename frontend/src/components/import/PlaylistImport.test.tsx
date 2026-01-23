import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, Mock, vi } from "vitest";
import { downloadsApi } from "../../api/downloads";
import { importApi } from "../../api/import";
import { useStore } from "../../store/useStore";
import { notify } from "../../utils/notify";
import PlaylistImport from "./PlaylistImport";

// Mock dependencies
vi.mock("../../api/import", () => ({
  importApi: {
    importPlaylist: vi.fn(),
    resolve: vi.fn(),
  },
}));

vi.mock("../../services/api");

vi.mock("../../api/downloads", () => ({
  downloadsApi: { add: vi.fn() },
}));

vi.mock("../../store/useStore");

vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Mock Lucide icons
vi.mock("lucide-react", async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    Upload: () => <div data-testid="icon-upload">Upload</div>,
    Loader2: () => <div data-testid="icon-loader">Loading</div>,
    CheckCircle2: () => <div data-testid="icon-check">Success</div>,
  };
});

describe("PlaylistImport Component", () => {
  // We don't need to mock addNotification on store anymore since we mock notify utils directly
  const mockFetchDownloads = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as Mock).mockReturnValue({
      fetchDownloads: mockFetchDownloads,
    });
  });

  it("renders import form", () => {
    render(<PlaylistImport />);
    expect(screen.getByText("Import Playlist")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Paste playlist URL here...")).toBeInTheDocument();
  });

  it("validates empty input", async () => {
    render(<PlaylistImport />);
    const btn = screen.getByText("Analyze");
    fireEvent.click(btn);
    // Should do nothing / no error toast because of early return
    expect(notify.error).not.toHaveBeenCalled();
  });

  it("handles successful import analysis and import", async () => {
    const mockTracks = [
      { title: "Track 1", artist: "Artist 1" },
      { title: "Track 2", artist: "Artist 2" },
    ];

    (importApi.importPlaylist as Mock).mockResolvedValue({
      job_id: "123",
      message: "Started",
      title: "Imported Playlist",
      tracks: mockTracks,
    });

    // Mock resolve for each track
    (importApi.resolve as Mock).mockImplementation((track) =>
      Promise.resolve({ ...track, id: "resolved-" + track.title })
    );

    render(<PlaylistImport />);

    const input = screen.getByPlaceholderText("Paste playlist URL here...");
    fireEvent.change(input, { target: { value: "https://spotify.com/playlist/123" } });

    const analyzeBtn = screen.getByText("Analyze");
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(screen.getByText("Imported Playlist")).toBeInTheDocument();
      expect(screen.getByText(/Found 2 tracks/)).toBeInTheDocument();
      expect(notify.success).toHaveBeenCalledWith("Found 2 tracks!");
    });

    // Now click Import All
    const importBtn = screen.getByText(/Import All/);
    fireEvent.click(importBtn);

    // Should queue tracks
    await waitFor(() => {
      expect(downloadsApi.add).toHaveBeenCalledTimes(2);
      expect(notify.success).toHaveBeenCalledWith("Successfully queued 2 tracks.");
      expect(mockFetchDownloads).toHaveBeenCalled();
    });
  });

  it("handles import error (empty)", async () => {
    (importApi.importPlaylist as Mock).mockResolvedValue({
      tracks: [],
    });

    render(<PlaylistImport />);
    const input = screen.getByPlaceholderText("Paste playlist URL here...");
    fireEvent.change(input, { target: { value: "empty-pl" } });
    fireEvent.click(screen.getByText("Analyze"));

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("No tracks found in this playlist.");
    });
  });

  it("handles API error", async () => {
    (importApi.importPlaylist as Mock).mockRejectedValue({
      response: { data: { detail: "Invalid URL" } },
    });

    render(<PlaylistImport />);
    const input = screen.getByPlaceholderText("Paste playlist URL here...");
    fireEvent.change(input, { target: { value: "bad-url" } });
    fireEvent.click(screen.getByText("Analyze"));

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Invalid URL");
    });
  });
});
