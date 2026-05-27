import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import api from "../services/api";
import { useStore } from "../store/useStore";
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
  default: ({ isOpen, onClose, trackIds }: any) =>
    isOpen ? (
      <div data-testid="add-playlist-modal" onClick={onClose}>
        Add {trackIds ? trackIds.join(",") : "No tracks"}
      </div>
    ) : null,
}));

// Mock Store
vi.mock("../store/useStore", () => ({
  useStore: vi.fn(),
}));

describe("Library Page Integration", () => {
  const mockFolders = {
    local: ["Playlist 1"],
    spotify: ["Spot Play 1"],
    youtube: [],
    soundcloud: [],
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

  const mockPlayTrack = vi.fn();
  const mockTogglePlay = vi.fn();

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

    // Setup default store mock
    (useStore as unknown as Mock).mockReturnValue({
      currentTrack: null,
      isPlaying: false,
      playTrack: mockPlayTrack,
      togglePlay: mockTogglePlay,
    });
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
    expect(screen.getByText("spotify")).toBeInTheDocument();
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
    fireEvent.click(screen.getByTitle("List View"));
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

    await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/downloads/1"));
    expect(notify.success).toHaveBeenCalledWith("Track deleted");
  });

  it("handles track deletion failure", async () => {
    (api.delete as any).mockRejectedValue(new Error("Failed"));
    await renderLibrary();
    fireEvent.click(screen.getByTitle("List View"));
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));
    await waitFor(() => screen.getByText("Bohemian Rhapsody"));

    const row = screen.getByText("Bohemian Rhapsody").closest("tr");
    const deleteBtn = within(row!).getByTitle("Delete File");
    fireEvent.click(deleteBtn);

    const confirmBtn = await screen.findByText("Delete");
    fireEvent.click(confirmBtn);

    await waitFor(() => expect(notify.error).toHaveBeenCalledWith("Failed to delete item"));
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

  it("handles playlist create failure", async () => {
    (api.post as any).mockRejectedValueOnce(new Error("Fail"));
    await renderLibrary();
    fireEvent.click(screen.getByText("library.newPlaylist"));
    const input = screen.getByLabelText("Playlist Name");
    fireEvent.change(input, { target: { value: "Fail List" } });
    fireEvent.click(screen.getByText("Create"));
    await waitFor(() => expect(notify.error).toHaveBeenCalledWith("Failed to create playlist"));
  });

  it("handles rescan functionality", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("library.rescan"));
    const confirmBtn = await screen.findByText("Rescan");
    fireEvent.click(confirmBtn);
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/downloads/rescan"));
    expect(notify.success).toHaveBeenCalledWith(expect.stringContaining("Found 5"));
  });

  it("handles rescan failure", async () => {
    (api.post as any).mockRejectedValueOnce(new Error("Fail"));
    await renderLibrary();
    fireEvent.click(screen.getByText("library.rescan"));
    const confirmBtn = await screen.findByText("Rescan");
    fireEvent.click(confirmBtn);
    await waitFor(() => expect(notify.error).toHaveBeenCalledWith("Rescan failed"));
  });

  it("handles track edit flow", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByTitle("List View"));
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));

    await waitFor(() => expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument());

    const row = screen.getByText("Bohemian Rhapsody").closest("tr");
    const editBtn = within(row!).getByTitle("Edit Info");
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

  it("handles audio playback interaction", async () => {
    // Setup store for this test
    (useStore as unknown as Mock).mockReturnValue({
      currentTrack: null,
      isPlaying: false,
      playTrack: mockPlayTrack,
      togglePlay: mockTogglePlay,
    });

    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));
    await waitFor(() => screen.getByText("Bohemian Rhapsody"));

    const image = screen.getByAltText("Bohemian Rhapsody");
    const button = image.closest("button");
    fireEvent.click(button!);

    expect(mockPlayTrack).toHaveBeenCalled();
  });

  it("toggles play if current track matches", async () => {
    // Setup store where mockItem1 is playing
    (useStore as unknown as Mock).mockReturnValue({
      currentTrack: { id: "t1" }, // matches mockItem1.track_id
      isPlaying: true,
      playTrack: mockPlayTrack,
      togglePlay: mockTogglePlay,
    });

    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));
    await waitFor(() => screen.getByText("Bohemian Rhapsody"));

    const image = screen.getByAltText("Bohemian Rhapsody");
    const button = image.closest("button");
    fireEvent.click(button!);

    expect(mockTogglePlay).toHaveBeenCalled();
    expect(mockPlayTrack).not.toHaveBeenCalled();
  });

  it("handles All Tracks selection", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("library.allTracks"));

    fireEvent.click(screen.getByText("library.allTracks"));
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/downloads/library",
        expect.objectContaining({ params: expect.objectContaining({ source: "local" }) })
      );
    });
  });

  it("handles search and filtering", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));
    await waitFor(() => screen.getByText("Bohemian Rhapsody"));

    const searchInput = screen.getByPlaceholderText("Search tracks...");
    fireEvent.change(searchInput, { target: { value: "Queen" } });

    expect(screen.getByText("Bohemian Rhapsody")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Hotel California")).not.toBeInTheDocument();
    });
  });

  it("handles Add to Playlist modal opening", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByTitle("List View"));
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));
    fireEvent.click(screen.getByText("Playlist 1"));
    await waitFor(() => screen.getByText("Bohemian Rhapsody"));

    const row = screen.getByText("Bohemian Rhapsody").closest("tr");
    const addBtn = within(row!).getByTitle("Add to Playlist");
    fireEvent.click(addBtn);

    expect(await screen.findByTestId("add-playlist-modal")).toBeInTheDocument();
    expect(screen.getByText("Add t1")).toBeInTheDocument();
  });

  it("renders different source icons", async () => {
    await renderLibrary();
    expect(screen.getByText("local")).toBeInTheDocument();
    expect(screen.getByText("spotify")).toBeInTheDocument();
    expect(screen.getByText("SC")).toBeInTheDocument(); // Soundcloud
  });

  it("handle playlist deletion", async () => {
    await renderLibrary();
    fireEvent.click(screen.getByText("local"));
    await waitFor(() => screen.getByText("Playlist 1"));

    // Find the playlist delete button by its hardcoded title
    const deleteBtn = screen.getByTitle("Delete playlist");
    fireEvent.click(deleteBtn);

    // Check for the modal.
    await waitFor(() => expect(screen.getByTestId("confirm-modal")).toBeInTheDocument());

    // There are multiple "Delete Playlist" texts (header and button), so we need to be specific
    const modal = screen.getByTestId("confirm-modal");
    const confirmBtn = within(modal).getByRole("button", { name: "Delete Playlist" });
    fireEvent.click(confirmBtn);

    await waitFor(() =>
      expect(api.delete).toHaveBeenCalledWith("/downloads/library/playlist", expect.anything())
    );
  });
});
