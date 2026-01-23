import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { syncApi } from "../../api/sync";
import { WatchlistItem } from "../../types";
import { notify } from "../../utils/notify";
import SyncModal from "./SyncModal";

// Mock dependencies
vi.mock("../../api/sync", () => ({
  syncApi: {
    analyze: vi.fn(),
    execute: vi.fn(),
  },
}));

vi.mock("../../utils/notify", () => ({
  notify: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, onClick, className, ...props }: any) => (
      <div className={className} onClick={onClick} {...props}>
        {children}
      </div>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Lucide icons seem to render fine or can be ignored usually, but if needed we can mock them.

const mockItem: WatchlistItem = {
  id: "1",
  source_name: "Test Playlist",
  source_type: "spotify",
  source_id: "sp1",
  target_path: "/music",
  sync_interval: 60,
  last_sync: "2023-01-01",
  created_at: "2023-01-01",
  status: "idle",
};

const mockReport = {
  sync_token: "abc-123",
  local_count: 10,
  remote_count: 12,
  to_remove_count: 2,
  to_remove_items: [
    { track_id: "t1", title: "Song A", artist: "Artist A", path: "/path/a" },
    { track_id: "t2", title: "Song B", artist: "Artist B", path: "/path/b" },
  ],
  safety_warning: false,
  warning_message: "",
};

const mockResult = {
  removed_from_playlist: 2,
  files_soft_deleted: 2,
  files_hard_deleted: 0,
  errors: [],
};

describe("SyncModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should not render if item is null", () => {
    render(<SyncModal item={null} onClose={() => {}} />);
    expect(screen.queryByText("Sync")).not.toBeInTheDocument();
  });

  it("should start analyzing when opened", async () => {
    // Need to return a promise that doesn't resolve immediately to check 'analyzing' state if we want,
    // but typically we wait for the effect.
    (syncApi.analyze as any).mockResolvedValue(mockReport);

    render(<SyncModal item={mockItem} onClose={() => {}} />);

    // Initially should show loader or analyzing text
    expect(screen.getByText("Analyzing playlist state...")).toBeInTheDocument();

    await waitFor(() => {
      expect(syncApi.analyze).toHaveBeenCalledWith(mockItem.id);
    });
  });

  it("should display report functionality in review step", async () => {
    (syncApi.analyze as any).mockResolvedValue(mockReport);

    render(<SyncModal item={mockItem} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("Local Tracks")).toBeInTheDocument();
    });

    expect(screen.getByText("10")).toBeInTheDocument(); // local count
    expect(screen.getByText("12")).toBeInTheDocument(); // remote count
    expect(screen.getByText("Song A")).toBeInTheDocument();
    expect(screen.getByText("Song B")).toBeInTheDocument();
    expect(screen.getByText("Tracks to Remove (2)")).toBeInTheDocument();
  });

  it("should handle selection of tracks to remove", async () => {
    const user = userEvent.setup();
    (syncApi.analyze as any).mockResolvedValue(mockReport);

    render(<SyncModal item={mockItem} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("Confirm Deletion")).toBeInTheDocument();
    });

    // Uncheck first item
    const checkboxA = screen.getAllByRole("checkbox")[0];
    await user.click(checkboxA);

    expect(screen.getByText("Tracks to Remove (1)")).toBeInTheDocument();

    // Check it back
    await user.click(checkboxA);
    expect(screen.getByText("Tracks to Remove (2)")).toBeInTheDocument();
  });

  it("should execute sync and show success", async () => {
    const user = userEvent.setup();
    (syncApi.analyze as any).mockResolvedValue(mockReport);
    (syncApi.execute as any).mockResolvedValue(mockResult);

    render(<SyncModal item={mockItem} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("Confirm Deletion")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Confirm Deletion"));

    // Should show expected calls
    expect(syncApi.execute).toHaveBeenCalledWith(mockItem.id, mockReport.sync_token, ["t1", "t2"]);

    await waitFor(() => {
      expect(screen.getByText("Sync Complete")).toBeInTheDocument();
    });

    expect(notify.success).toHaveBeenCalledWith("Sync completed successfully");
  });

  it("should handle errors during analysis", async () => {
    (syncApi.analyze as any).mockRejectedValue(new Error("Network error"));
    const onClose = vi.fn();

    render(<SyncModal item={mockItem} onClose={onClose} />);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Analysis failed. See console.");
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("should handle errors during execution", async () => {
    const user = userEvent.setup();
    (syncApi.analyze as any).mockResolvedValue(mockReport);
    (syncApi.execute as any).mockRejectedValue(new Error("Exec error"));

    render(<SyncModal item={mockItem} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("Confirm Deletion")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Confirm Deletion"));

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Execution failed");
    });
    // Should return to review step (button still visible)
    expect(screen.getByText("Confirm Deletion")).toBeInTheDocument();
  });
});
