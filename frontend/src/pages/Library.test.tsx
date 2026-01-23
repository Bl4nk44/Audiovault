import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, Mock, vi } from "vitest";
import api from "../services/api";
import { notify } from "../utils/notify";
import Library from "./Library";

// Mock dependencies
vi.mock("../services/api");
vi.mock("../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../hooks/useTranslation", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../components/ui/ConfirmModal", () => ({
  default: ({ isOpen, onConfirm, onCancel, title, confirmText }: any) => {
    if (!isOpen) return null;
    return (
      <div data-testid="confirm-modal">
        <h1>{title}</h1>
        <button onClick={onConfirm}>{confirmText || "Confirm"}</button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    );
  },
}));

vi.mock("../components/AddToPlaylistModal", () => ({
  default: ({ isOpen, onClose, trackId }: any) =>
    isOpen ? (
      <div data-testid="add-playlist-modal" onClick={onClose}>
        Add {trackId}
      </div>
    ) : null,
}));

describe("Library Page Integration", () => {
  const mockFolders = {
    local: ["Playlist 1"],
    spotify: ["Spot Play 1"],
  };

  const mockItem1 = {
    id: "1",
    track_id: "t1",
    status: "completed",
    created_at: "2023-01-01",
    track: {
      title: "Bohemian Rhapsody",
      artist: "Queen",
      album: "A Night at the Opera",
      image_url: "cover.jpg",
      filename: "queen.mp3",
    },
  };

  const mockItem2 = {
    id: "2",
    track_id: "t2",
    status: "completed",
    created_at: "2023-01-02",
    track: {
      title: "Hotel California",
      artist: "Eagles",
      album: "Hotel California",
    },
  };

  const mockLibraryResponse = {
    items: [mockItem1, mockItem2],
    total: 2,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockImplementation((url: string) => {
      if (url === "/downloads/library/folders") {
        return Promise.resolve({ data: mockFolders });
      }
      if (url === "/downloads/library") {
        return Promise.resolve({ data: mockLibraryResponse });
      }
      return Promise.resolve({ data: {} });
    });

    (api.delete as any).mockResolvedValue({});
    (api.post as any).mockResolvedValue({ data: { rescanned_count: 5 } });
    (api.put as any).mockResolvedValue({});
  });

  const renderLibrary = async () => {
    await act(async () => {
      render(
        <BrowserRouter>
          <Library />
        </BrowserRouter>
      );
    });
  };

  it("loads and displays folders initially", async () => {
    await renderLibrary();
    expect(screen.getByText("local")).toBeInTheDocument();
  });

  it("navigates to playlist and displays tracks", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/downloads/library",
        expect.objectContaining({
          params: expect.objectContaining({ playlist: "Playlist 1" }),
        })
      );
      expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument();
    });
  });

  it("handles track deletion flow", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));

    await waitFor(() => expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument());

    const row = screen.getByText("Bohemian Rhapsody").closest("tr");
    if (!row) throw new Error("Row not found");

    const deleteBtn = within(row).getByTitle("Delete File");
    fireEvent.click(deleteBtn);

    const confirmBtn = await screen.findByText("Delete");
    fireEvent.click(confirmBtn);

    await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/downloads/remove/1"));
    expect(notify.success).toHaveBeenCalledWith("Track deleted");
  });

  it("handles playlist update/create", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("library.newPlaylist"));

    const input = screen.getByLabelText("Playlist Name");
    fireEvent.change(input, { target: { value: "My New List" } });

    const createBtn = screen.getByText("Create");
    fireEvent.click(createBtn);

    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/playlists/", expect.anything()));
  });

  it("handles rescan functionality", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("library.rescan"));
    const confirmBtn = await screen.findByText("Rescan");
    fireEvent.click(confirmBtn);
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/downloads/rescan"));
    expect(notify.success).toHaveBeenCalledWith(expect.stringContaining("Found 5"));
  });

  it("handles track edit flow", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));

    await waitFor(() => expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument());

    const row = screen.getByText("Bohemian Rhapsody").closest("tr");
    if (!row) throw new Error("Row not found");

    const editBtn = within(row).getByTitle("Edit Info");
    fireEvent.click(editBtn);

    await waitFor(() => expect(screen.getByLabelText("Title")).toBeInTheDocument());

    const titleInput = screen.getByLabelText("Title");
    fireEvent.change(titleInput, { target: { value: "Bohemian Rhapsody (Remastered)" } });

    const saveBtn = screen.getByText("Save Changes");
    fireEvent.click(saveBtn);

    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith(
        "/downloads/library/1",
        expect.objectContaining({ title: "Bohemian Rhapsody (Remastered)" })
      )
    );
    expect(notify.success).toHaveBeenCalledWith("Track updated");
  });

  it("handles breadcrumb navigation", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => expect(screen.getByText("Playlist 1")).toBeInTheDocument());

    // Breadcrumb for the service should be present (capitalized in code)
    expect(screen.getByText(/Local/i)).toBeInTheDocument();

    // Click on root breadcrumb
    const rootBreadcrumb = screen.getByText("sidebar.library");
    fireEvent.click(rootBreadcrumb);

    await waitFor(() => {
      expect(screen.queryByText("Playlist 1")).not.toBeInTheDocument();
      expect(screen.getByText("local")).toBeInTheDocument();
    });
  });

  it("handles search filtering in playlist view", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));

    await waitFor(() => expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument());
    expect(screen.getAllByText("Hotel California").length).toBeGreaterThan(0);

    const searchInput = screen.getByPlaceholderText("Search tracks...");
    fireEvent.change(searchInput, { target: { value: "Queen" } });

    await waitFor(() => {
      expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument();
      // Using queryAllByText to verify it's gone
      expect(screen.queryAllByText("Hotel California").length).toBe(0);
    });
  });

  it("handles pagination clicks", async () => {
    // Return many items to trigger pagination?
    // Or just mock the total count.
    (api.get as Mock).mockImplementation((url: string) => {
      if (url === "/downloads/library") {
        return Promise.resolve({
          data: {
            items: Array(50)
              .fill(mockItem1)
              .map((item, i) => ({ ...item, id: `p${i}` })),
            total: 120,
          },
        });
      }
      return Promise.resolve({ data: mockFolders });
    });

    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));

    await waitFor(() => expect(screen.getByText("Page 1 of 3")).toBeInTheDocument());

    const nextBtn = screen.getByText("Next");
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/downloads/library",
        expect.objectContaining({
          params: expect.objectContaining({ skip: 50 }),
        })
      );
    });
  });
});
