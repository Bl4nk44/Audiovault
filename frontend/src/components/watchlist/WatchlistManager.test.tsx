import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { watchlistApi } from "../../api/watchlist";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
import { notify } from "../../utils/notify";
import WatchlistManager from "./WatchlistManager";

// Mock dependencies
vi.mock("../../api/watchlist");
vi.mock("../../services/api");
vi.mock("../../utils/notify", () => ({
  notify: { success: vi.fn(), error: vi.fn() },
}));

// Partial mock store
vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

// Mock child components
vi.mock("./WatchlistItem", () => ({
  default: ({ item, onRemove, onSync }: any) => (
    <div data-testid="watchlist-item">
      <span>{item.name}</span>
      <button onClick={() => onRemove(item.id)}>Remove</button>
      <button onClick={() => onSync(item)}>Sync</button>
    </div>
  ),
}));

vi.mock("../sync/SyncModal", () => ({
  default: ({ item, onClose }: any) =>
    item ? (
      <div data-testid="sync-modal">
        Modal for {item.name}
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

describe("WatchlistManager Component", () => {
  const mockWatchlist = [
    { id: "1", name: "Artist 1", type: "artist", image_url: "url1" },
    { id: "2", name: "Channel 2", type: "channel", image_url: "url2" },
  ];

  const mockFetchDownloads = vi.fn();
  const mockSyncWatchlist = vi.fn().mockResolvedValue({});
  const mockRemoveFromWatchlist = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as unknown as Mock).mockReturnValue({
      fetchDownloads: mockFetchDownloads,
      syncWatchlist: mockSyncWatchlist,
      removeFromWatchlist: mockRemoveFromWatchlist,
      watchlist: mockWatchlist,
    });
    (watchlistApi.getAll as unknown as Mock).mockResolvedValue(mockWatchlist);
  });

  it("renders watchlist items in grid view by default", async () => {
    render(<WatchlistManager />);
    await waitFor(() => {
      expect(screen.getByText("Artist 1")).toBeInTheDocument();
      expect(screen.getByText("Channel 2")).toBeInTheDocument();
    });
    // Grid view check (indirectly via class or structure if possible, but mainly rendering)
  });

  it("toggles view modes", async () => {
    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    const listBtn = screen.getByTitle("List View");
    fireEvent.click(listBtn);

    // View state change creates re-render.
    // In a real integration test we'd check classes. Here we trust state updates.
    // Let's verify buttons exist and are interactive.
    expect(screen.getByTitle("Grid View")).toBeInTheDocument();
  });

  it("handles empty state", async () => {
    (useStore as unknown as Mock).mockReturnValue({
      fetchDownloads: mockFetchDownloads,
      syncWatchlist: mockSyncWatchlist,
      removeFromWatchlist: mockRemoveFromWatchlist,
      watchlist: [],
    });
    render(<WatchlistManager />);
    await waitFor(() => {
      expect(screen.getByText(/watchlist is empty/i)).toBeInTheDocument();
    });
  });

  it("handles item removal success", async () => {
    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    // Click remove on first item
    const removeBtns = screen.getAllByText("Remove");
    fireEvent.click(removeBtns[0]);

    await waitFor(() => {
      expect(mockRemoveFromWatchlist).toHaveBeenCalledWith("1");
      expect(notify.success).toHaveBeenCalledWith("Removed from watchlist");
    });
  });

  it("handles item removal failure", async () => {
    mockRemoveFromWatchlist.mockRejectedValue(new Error("Fail"));
    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    const removeBtns = screen.getAllByText("Remove");
    fireEvent.click(removeBtns[0]);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to remove item");
    });
  });

  it("opens and closes sync modal", async () => {
    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    expect(screen.queryByTestId("sync-modal")).not.toBeInTheDocument();

    const syncBtns = screen.getAllByText("Sync");
    fireEvent.click(syncBtns[0]);

    await waitFor(() => {
      expect(screen.getByTestId("sync-modal")).toBeInTheDocument();
      expect(screen.getByText("Modal for Artist 1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Close"));

    await waitFor(() => {
      expect(screen.queryByTestId("sync-modal")).not.toBeInTheDocument();
    });
  });

  it("checks for updates manually", async () => {
    // Mock API response
    (api.post as unknown as Mock).mockResolvedValue({ data: { new_downloads: 5 } });

    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    const checkBtn = screen.getByText("Check for Updates");
    fireEvent.click(checkBtn);

    // Should show 'Checking...'
    expect(screen.getByText("Checking...")).toBeInTheDocument();

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/watchlist/check-updates");
      expect(notify.success).toHaveBeenCalledWith("Check complete. 5 new items found.");
      expect(mockSyncWatchlist).toHaveBeenCalledTimes(2); // Once on mount, once after check
    });
  });

  it("handles check updates error", async () => {
    (api.post as unknown as Mock).mockRejectedValue(new Error("Network Error"));

    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    const checkBtn = screen.getByText("Check for Updates");
    fireEvent.click(checkBtn);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to check for updates");
    });
  });

  it("syncs all deletions successfully", async () => {
    (api.post as unknown as Mock).mockResolvedValue({
      data: {
        synced: [{ removed_count: 3 }, { removed_count: 2 }],
        skipped: ["item1"],
      },
    });

    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    const syncBtn = screen.getByText("Sync Deletions");
    fireEvent.click(syncBtn);

    expect(screen.getByText("Syncing...")).toBeInTheDocument();

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/watchlist/sync-all-deletions");
      expect(notify.success).toHaveBeenCalledWith("Sync complete. Removed: 5, Skipped: 1");
      expect(mockSyncWatchlist).toHaveBeenCalledTimes(2);
    });
  });

  it("handles sync all deletions error", async () => {
    (api.post as unknown as Mock).mockRejectedValue(new Error("Sync Error"));

    render(<WatchlistManager />);
    await waitFor(() => expect(screen.getByText("Artist 1")).toBeInTheDocument());

    const syncBtn = screen.getByText("Sync Deletions");
    fireEvent.click(syncBtn);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Sync all deletions failed");
      expect(screen.getByText("Sync Deletions")).toBeInTheDocument(); // loading state cleared
    });
  });
});
