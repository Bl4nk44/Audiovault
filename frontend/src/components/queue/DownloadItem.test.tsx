import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { downloadsApi } from "../../api/downloads";
import { useStore } from "../../store/useStore";
import DownloadItem from "./DownloadItem";

// Mock dependencies
vi.mock("../../store/useStore");
vi.mock("../../api/downloads", () => ({
  downloadsApi: { remove: vi.fn() },
}));
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className, onClick }: any) => (
      <div className={className} onClick={onClick}>
        {children}
      </div>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));
vi.mock("../../lib/utils", () => ({
  cn: (...args: any[]) => args.join(" "),
}));

describe("DownloadItem Component", () => {
  const mockStore = {
    playTrack: vi.fn(),
    pauseDownload: vi.fn(),
    resumeDownload: vi.fn(),
    retryDownload: vi.fn(),
    removeFromQueue: vi.fn(),
  };

  const mockItem = {
    id: "1",
    track: { title: "Test Song", artist: "Test Artist", image_url: "test.jpg" },
    status: "downloading",
    progress: 50,
    error_message: "",
  } as any;

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as any).mockReturnValue(mockStore);
  });

  it("renders item details", () => {
    render(<DownloadItem item={mockItem} />);
    expect(screen.getByText("Test Song")).toBeInTheDocument();
    expect(screen.getByText("Test Artist")).toBeInTheDocument();
    expect(screen.getByText("Downloading")).toBeInTheDocument(); // Default badge text
  });

  it("handles pause action", () => {
    render(<DownloadItem item={mockItem} />);
    // Find by Pause Icon title
    const pauseBtn = screen.getByTitle("Pause");
    fireEvent.click(pauseBtn);
    expect(mockStore.pauseDownload).toHaveBeenCalledWith("1");
  });

  it("handles resume action", () => {
    render(<DownloadItem item={{ ...mockItem, status: "paused" }} />);
    const resumeBtn = screen.getByTitle("Resume");
    fireEvent.click(resumeBtn);
    expect(mockStore.resumeDownload).toHaveBeenCalledWith("1");
  });

  it("handles retry action", () => {
    render(<DownloadItem item={{ ...mockItem, status: "failed" }} />);
    const retryBtn = screen.getByTitle("Retry Download");
    fireEvent.click(retryBtn);
    expect(mockStore.retryDownload).toHaveBeenCalledWith("1");
  });

  it("shows delete confirmation modal", () => {
    render(<DownloadItem item={{ ...mockItem, status: "completed" }} />);
    const deleteBtn = screen.getByTitle("Delete file");
    fireEvent.click(deleteBtn);

    // Confirm modal should appear
    expect(screen.getByText("Delete File")).toBeInTheDocument();

    // Confirm delete
    const confirmBtn = screen.getByText("Delete");
    fireEvent.click(confirmBtn);

    expect(mockStore.removeFromQueue).toHaveBeenCalledWith("1");
    expect(downloadsApi.remove).toHaveBeenCalledWith("1");
  });
});
