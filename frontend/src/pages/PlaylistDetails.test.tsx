import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { playlistsApi } from "../api/playlists";
import { useStore } from "../store/useStore";
import { notify } from "../utils/notify";
import PlaylistDetails from "./PlaylistDetails";

// Mock dependencies
const mockNavigate = vi.fn();
let mockSource = "local";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...(actual as any),
    useParams: () => ({ id: "1" }),
    useLocation: () => ({ state: { source: mockSource } }),
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual("@tanstack/react-query");
  return {
    ...(actual as any),
    useQuery: vi.fn(),
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

vi.mock("../api/playlists");

const mockAddToWatchlist = vi.fn();
const mockRemoveFromWatchlist = vi.fn();

vi.mock("../store/useStore", () => ({
  useStore: vi.fn(() => ({
    watchlist: [],
    addToWatchlist: mockAddToWatchlist,
    removeFromWatchlist: mockRemoveFromWatchlist,
  })),
}));

vi.mock("../utils/notify", () => ({
  notify: { success: vi.fn(), error: vi.fn() },
}));

// Mock child components
vi.mock("../components/search/TrackCard", () => ({
  default: ({ track, onRemove }: any) => (
    <div data-testid="track-card">
      {track.title}
      {onRemove && (
        <button onClick={() => onRemove(track.id)} data-testid="remove-track-btn">
          Remove
        </button>
      )}
    </div>
  ),
}));

vi.mock("../components/ui/ConfirmModal", () => ({
  default: ({ isOpen, title, onConfirm, onClose }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        {title}
        <button onClick={onConfirm}>Confirm</button>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

import { useQuery } from "@tanstack/react-query";

describe("PlaylistDetails Page", () => {
  const mockPlaylist = {
    id: "1",
    title: "Test Playlist",
    description: "Test Desc",
    image_url: "test.jpg",
    tracks: [{ id: "t1", title: "Song A", artist: "Artist A", duration_ms: 60000 }],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockSource = "local";
    (useQuery as unknown as Mock).mockReturnValue({
      data: mockPlaylist,
      isLoading: false,
      error: null,
    });
    (useStore as unknown as Mock).mockReturnValue({
      watchlist: [],
      addToWatchlist: mockAddToWatchlist,
      removeFromWatchlist: mockRemoveFromWatchlist,
    });
  });

  it("renders playlist details and tracks", () => {
    render(<PlaylistDetails />);
    expect(screen.getByText("Test Playlist")).toBeInTheDocument();
    expect(screen.getByText("Test Desc")).toBeInTheDocument();
    expect(screen.getByText("Song A")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    (useQuery as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });
    const { container } = render(<PlaylistDetails />);
    // Check for animate-spin class which is on the loader
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows error state", () => {
    (useQuery as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error("Fail"),
    });
    render(<PlaylistDetails />);
    expect(screen.getByText("Failed to load playlist")).toBeInTheDocument();
  });

  it("handles edit playlist name", async () => {
    (playlistsApi.update as unknown as Mock).mockResolvedValue({});
    render(<PlaylistDetails />);

    fireEvent.click(screen.getByText("Edit"));
    const input = screen.getByLabelText("Name");
    fireEvent.change(input, { target: { value: "Updated Name" } });
    fireEvent.click(screen.getByText("Save Changes"));

    await waitFor(() => {
      expect(playlistsApi.update).toHaveBeenCalledWith("1", { name: "Updated Name" });
      expect(notify.success).toHaveBeenCalledWith("Playlist updated");
    });
  });

  it("handles delete playlist", async () => {
    (playlistsApi.delete as unknown as Mock).mockResolvedValue({});
    render(<PlaylistDetails />);

    fireEvent.click(screen.getByText("Delete"));
    expect(screen.getByTestId("confirm-modal")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Confirm"));

    await waitFor(() => {
      expect(playlistsApi.delete).toHaveBeenCalledWith("1");
      expect(mockNavigate).toHaveBeenCalledWith("/library");
    });
  });

  it("handles track removal", async () => {
    (playlistsApi.removeTracks as unknown as Mock).mockResolvedValue({});
    render(<PlaylistDetails />);

    // Click remove on track card
    fireEvent.click(screen.getByTestId("remove-track-btn"));

    // Confirm in modal
    expect(screen.getByText("Remove Track")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Confirm"));

    await waitFor(() => {
      expect(playlistsApi.removeTracks).toHaveBeenCalledWith("1", ["t1"]);
      expect(notify.success).toHaveBeenCalledWith("Track removed from playlist");
    });
  });

  it("handles watchlist toggle (add)", () => {
    render(<PlaylistDetails />);
    fireEvent.click(screen.getByText("Follow"));
    expect(mockAddToWatchlist).toHaveBeenCalled();
    expect(notify.success).toHaveBeenCalledWith("Added to watchlist");
  });

  it("handles watchlist toggle (remove)", () => {
    (useStore as unknown as Mock).mockReturnValue({
      watchlist: [{ id: "w1", source_id: "1" }],
      addToWatchlist: mockAddToWatchlist,
      removeFromWatchlist: mockRemoveFromWatchlist,
    });
    render(<PlaylistDetails />);
    fireEvent.click(screen.getByText("Following"));
    expect(mockRemoveFromWatchlist).toHaveBeenCalledWith("w1");
    expect(notify.success).toHaveBeenCalledWith("Removed from watchlist");
  });

  it("handles playlist export", async () => {
    (playlistsApi.exportAsJson as unknown as Mock).mockResolvedValue({});
    render(<PlaylistDetails />);

    fireEvent.click(screen.getByText("Export JSON"));
    await waitFor(() => {
      expect(playlistsApi.exportAsJson).toHaveBeenCalledWith("1", "Test Playlist");
      expect(notify.success).toHaveBeenCalledWith("Playlist exported successfully");
    });
  });

  it("handles export error", async () => {
    (playlistsApi.exportAsJson as unknown as Mock).mockRejectedValue(new Error());
    render(<PlaylistDetails />);

    fireEvent.click(screen.getByText("Export JSON"));
    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to export playlist");
    });
  });

  it("does not show local actions for non-local playlists", () => {
    mockSource = "spotify";
    render(<PlaylistDetails />);
    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    expect(screen.queryByText("Export JSON")).not.toBeInTheDocument();
  });
});
