import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import api from "../../services/api";
import { notify } from "../../utils/notify";
import WatchlistItem from "./WatchlistItem";

// Mock dependencies
vi.mock("../../services/api");
vi.mock("../../utils/notify", () => ({ notify: { success: vi.fn(), error: vi.fn() } }));
vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

describe("WatchlistItem Component", () => {
  const mockItem = {
    id: "1",
    source_name: "Test Playlist",
    watch_type: "playlist",
    source: "spotify",
    metadata_content: { image_url: "test.jpg" },
    auto_download: true,
    new_items_count: 5,
    source_id: "sid1",
  } as any;

  const mockOnRemove = vi.fn();
  const mockOnSync = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders item details in grid view", () => {
    render(<WatchlistItem item={mockItem} onRemove={mockOnRemove} viewMode="grid" />);
    expect(screen.getByText("Test Playlist")).toBeInTheDocument();
  });

  it("handles auto-download toggle successfully", async () => {
    (api.patch as unknown as Mock).mockResolvedValue({});
    render(<WatchlistItem item={mockItem} onRemove={mockOnRemove} />);

    const toggleBtn = screen.getByTitle("Auto-download: ON");
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(api.patch).toHaveBeenCalledWith(
        "/watchlist/1",
        expect.objectContaining({ auto_download: false })
      );
      expect(notify.success).toHaveBeenCalledWith("Auto-download disabled");
    });
  });

  it("handles auto-download toggle failure", async () => {
    (api.patch as unknown as Mock).mockRejectedValue(new Error("Fail"));
    render(<WatchlistItem item={mockItem} onRemove={mockOnRemove} />);

    const toggleBtn = screen.getByTitle("Auto-download: ON");
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to update settings");
      expect(screen.getByTitle("Auto-download: ON")).toBeInTheDocument(); // Reverted
    });
  });

  it("handles sync action for playlist", () => {
    render(<WatchlistItem item={mockItem} onRemove={mockOnRemove} onSync={mockOnSync} />);
    const syncBtn = screen.getByTitle("watchlist.syncDeletions");
    fireEvent.click(syncBtn);
    expect(mockOnSync).toHaveBeenCalledWith(mockItem);
  });

  it("navigates to artist profile", () => {
    const artistItem = { ...mockItem, watch_type: "artist", source_id: "artist1" };
    render(<WatchlistItem item={artistItem} onRemove={mockOnRemove} />);

    fireEvent.click(screen.getByText("Test Playlist"));
    expect(mockNavigate).toHaveBeenCalledWith("/artist/artist1");
  });

  it("handles image error by showing fallback", async () => {
    const { container } = render(<WatchlistItem item={mockItem} onRemove={mockOnRemove} />);
    const img = screen.queryByAltText("Test Playlist");
    if (img) fireEvent.error(img);

    await waitFor(() => {
      // Fallback should show first letter of source
      const fallback = container.querySelector(".uppercase");
      expect(fallback).not.toBeNull();
      expect(fallback?.textContent).toBe("s"); // Component uses item.source?.[0]
    });
  });

  it("renders with list view by default", () => {
    render(<WatchlistItem item={mockItem} onRemove={mockOnRemove} />);
    expect(screen.getByText("spotify • playlist")).toBeInTheDocument();
  });
});
