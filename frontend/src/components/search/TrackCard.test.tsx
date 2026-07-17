import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
import { notify } from "../../utils/notify";
import TrackCard from "./TrackCard";

const mockPlayTrack = vi.fn();
const mockTogglePlay = vi.fn();
const mockNavigate = vi.fn();

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("../../services/api", () => ({
  default: { post: vi.fn() },
}));

vi.mock("../../utils/notify", () => ({
  notify: { success: vi.fn(), error: vi.fn() },
}));

const mockAddToPlaylistModal = vi.fn();

vi.mock("../AddToPlaylistModal", () => ({
  default: (props: any) => {
    mockAddToPlaylistModal(props);
    const { isOpen, onClose } = props;
    return isOpen ? (
      <div data-testid="add-modal">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null;
  },
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => (
      <div {...props} onClick={onClick} data-testid="track-card">
        {children}
      </div>
    ),
    button: ({ children, onClick, ...props }: any) => (
      <button {...props} onClick={onClick}>
        {children}
      </button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe("TrackCard", () => {
  const mockTrack = {
    id: "t1",
    title: "Test Track",
    artist: "Test Artist",
    artist_id: "a1",
    cover: "test.jpg",
    source: "spotify",
    duration_ms: 180000,
  } as any;

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as unknown as Mock).mockReturnValue({
      playTrack: mockPlayTrack,
      togglePlay: mockTogglePlay,
      currentTrack: null,
      isPlaying: false,
    });
  });

  it("handles play action", () => {
    render(<TrackCard track={mockTrack} />);
    fireEvent.click(screen.getByTestId("track-card"));
    expect(mockPlayTrack).toHaveBeenCalled();
  });

  it("handles download action success", async () => {
    (api.post as unknown as Mock).mockResolvedValue({ data: { task_id: "job1" } });
    render(<TrackCard track={mockTrack} />);

    const downloadBtn = screen.getByTitle("Download");
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/downloads/add",
        expect.objectContaining({
          track_id: "t1",
          source: "spotify",
        })
      );
      expect(notify.success).toHaveBeenCalledWith("Added to download queue");
    });
  });

  it("handles download action error", async () => {
    (api.post as unknown as Mock).mockRejectedValue(new Error("Fail"));
    render(<TrackCard track={mockTrack} />);

    fireEvent.click(screen.getByTitle("Download"));

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to add to queue");
    });
  });

  it("navigates to spotify artist profile if artist_id is missing", () => {
    const track = { ...mockTrack, artist_id: undefined, spotify_artist_id: "s1" };
    render(<TrackCard track={track} />);
    fireEvent.click(screen.getByText("Test Artist"));
    expect(mockNavigate).toHaveBeenCalledWith("/artist/s1");
  });

  it("toggles add to playlist modal", () => {
    render(<TrackCard track={mockTrack} />);
    fireEvent.click(screen.getByTitle("Add to Playlist"));
    expect(screen.getByTestId("add-modal")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Close"));
    expect(screen.queryByTestId("add-modal")).not.toBeInTheDocument();
  });

  it("maps non-UUID provider track id to external trackIds for AddToPlaylistModal", () => {
    const track = { ...mockTrack, id: "3135556", artist: "Test Artist", title: "Test Track" };
    render(<TrackCard track={track} />);
    fireEvent.click(screen.getByTitle("Add to Playlist"));

    expect(mockAddToPlaylistModal).toHaveBeenLastCalledWith(
      expect.objectContaining({
        trackIds: ["external:Test Artist:Test Track"],
      })
    );
  });

  it("passes library UUID track id through unchanged to AddToPlaylistModal", () => {
    const track = { ...mockTrack, id: "550e8400-e29b-41d4-a716-446655440000" };
    render(<TrackCard track={track} />);
    fireEvent.click(screen.getByTitle("Add to Playlist"));

    expect(mockAddToPlaylistModal).toHaveBeenLastCalledWith(
      expect.objectContaining({
        trackIds: ["550e8400-e29b-41d4-a716-446655440000"],
      })
    );
  });
});
