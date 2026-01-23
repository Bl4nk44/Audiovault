import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, Mock, vi } from "vitest";
import { downloadsApi } from "../../api/downloads";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
import DownloadQueue from "./DownloadQueue";

// Mock dependencies
vi.mock("../../services/api");
vi.mock("../../api/downloads", () => ({
  downloadsApi: {
    restartAll: vi.fn(),
    clearAll: vi.fn(),
    remove: vi.fn(),
  },
}));
vi.mock("../../store/useStore");

vi.mock("./DownloadItem", () => ({
  default: ({ item }: any) => (
    <div data-testid="download-item">
      {item.track.title} - {item.status}
    </div>
  ),
}));

vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: any) => <>{children}</>,
  motion: {
    div: ({ children, className }: any) => <div className={className}>{children}</div>,
  },
}));

describe("DownloadQueue Component", () => {
  const mockQueue = [
    {
      id: "1",
      track: { title: "Song 1", artist: "Artist 1" },
      status: "downloading",
      progress: 50,
    },
    { id: "2", track: { title: "Song 2", artist: "Artist 2" }, status: "completed", progress: 100 },
  ];

  const mockAddNotification = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as Mock).mockReturnValue({ addNotification: mockAddNotification });
    (api.get as Mock).mockResolvedValue({ data: mockQueue });
  });

  it("fetches and displays queue items", async () => {
    render(<DownloadQueue />);
    await waitFor(() => {
      expect(screen.getByText("Song 1 - downloading")).toBeInTheDocument();
      expect(screen.getByText("Song 2 - completed")).toBeInTheDocument();
    });
  });

  it("displays empty state when queue is empty", async () => {
    (api.get as Mock).mockResolvedValue({ data: [] });
    render(<DownloadQueue />);
    await waitFor(() => {
      expect(screen.getByText("Queue is empty")).toBeInTheDocument();
    });
  });

  it("handles realtime progress updates", async () => {
    render(<DownloadQueue />);
    await waitFor(() => expect(screen.getByText("Song 1 - downloading")).toBeInTheDocument());

    const completedEvent = new CustomEvent("download:progress", {
      detail: { download_id: "1", progress: 100, status: "completed" },
    });

    act(() => {
      globalThis.dispatchEvent(completedEvent);
    });

    await waitFor(() => {
      expect(screen.getByText("Song 1 - completed")).toBeInTheDocument(); // Was downloading, now completed locally via event
    });
  });

  it("handles restart all", async () => {
    render(<DownloadQueue />);
    await waitFor(() => expect(screen.getByText("Song 1 - downloading")).toBeInTheDocument());

    const restartBtn = screen.getByText("Restart All");
    fireEvent.click(restartBtn);

    await waitFor(() => {
      expect(downloadsApi.restartAll).toHaveBeenCalled();
      expect(mockAddNotification).toHaveBeenCalledWith("success", expect.any(String));
      expect(api.get).toHaveBeenCalledTimes(2); // Initial fetch + refresh after restart
    });
  });

  it("handles clear all", async () => {
    render(<DownloadQueue />);
    await waitFor(() => expect(screen.getByText("Song 1 - downloading")).toBeInTheDocument());

    const clearBtn = screen.getByText("Clear All");
    fireEvent.click(clearBtn);

    await waitFor(() => {
      expect(downloadsApi.clearAll).toHaveBeenCalled();
      expect(mockAddNotification).toHaveBeenCalledWith("success", expect.any(String));
      expect(api.get).toHaveBeenCalledTimes(2);
    });
  });

  it("handles error during fetch", async () => {
    (api.get as Mock).mockRejectedValue(new Error("Fail"));
    render(<DownloadQueue />);
    await waitFor(() => {
      expect(mockAddNotification).toHaveBeenCalledWith("error", expect.any(String));
    });
  });
});
