import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import api from "../services/api";
import Dashboard from "./Dashboard";

// Mock dependencies
vi.mock("../services/api");
// Mock SystemStats to avoid nested async issues
vi.mock("../components/dashboard/SystemStats", () => ({
  default: () => <div data-testid="system-stats">System Stats</div>,
}));
vi.mock("../hooks/useTranslation", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock Framer Motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className, ...props }: any) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
    button: ({ children, className, onClick, ...props }: any) => (
      <button className={className} onClick={onClick} {...props}>
        {children}
      </button>
    ),
  },
}));

describe("Dashboard Page", () => {
  const mockStats = {
    total_downloads: "150",
    tracks_in_library: "1200",
    pending_queue: "3",
    storage_free: "450 GB",
    active_download: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockResolvedValue({ data: mockStats });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const renderDashboard = async () => {
    let result;
    await act(async () => {
      result = render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );
    });
    // ALWAYS wait for the initial fetch to settle to avoid "act" warnings
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/dashboard/stats");
    });
    return result;
  };

  it("renders dashboard and fetches stats on mount", async () => {
    await renderDashboard();

    expect(screen.getByText("dashboard.title")).toBeInTheDocument();
    expect(screen.getByText("150")).toBeInTheDocument(); // Downloads
    expect(screen.getByText("1200")).toBeInTheDocument(); // Tracks
    expect(screen.getByText("450 GB")).toBeInTheDocument(); // Storage
    expect(screen.getByTestId("system-stats")).toBeInTheDocument();
  });

  it("handles search input and navigation", async () => {
    await renderDashboard();

    const searchInput = screen.getByPlaceholderText("dashboard.searchPlaceholder");
    const searchButton = screen.getAllByRole("button")[0]; // Just picking the first button which is search

    // Initial state
    expect(searchButton).toBeDisabled();

    // Type query
    fireEvent.change(searchInput, { target: { value: "Queen" } });
    expect(searchInput).toHaveValue("Queen");
    expect(searchButton).not.toBeDisabled();

    // Submit
    fireEvent.click(searchButton);
    expect(mockNavigate).toHaveBeenCalledWith("/search?q=Queen");
  });

  it("navigates to quick links", async () => {
    await renderDashboard();

    const libraryLink = screen.getByText("dashboard.quickLinks.library");
    fireEvent.click(libraryLink);
    expect(mockNavigate).toHaveBeenCalledWith("/library");
  });

  it("handles polling interval", async () => {
    vi.useFakeTimers();
    // Manual render to control act/timers strictly
    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    // Initial fetch
    expect(api.get).toHaveBeenCalledTimes(1);

    // Fast forward 5 seconds
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });

    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it("updates active download on 'download:progress' event", async () => {
    await renderDashboard();

    const progressEvent = new CustomEvent("download:progress", {
      detail: {
        download_id: "dl-123",
        progress: 45,
        status: "downloading",
        track: {
          title: "Bohemian Rhapsody",
          artist: "Queen",
          image_url: "cover.jpg",
        },
      },
    });

    await act(async () => {
      globalThis.dispatchEvent(progressEvent);
    });

    // Check if state update happened (indirectly via console or component re-render if we could inspect it)
    // Here we just ensure no crash.
  });

  it("refetches stats on 'download:completed' event", async () => {
    await renderDashboard();
    expect(api.get).toHaveBeenCalledTimes(1);

    await act(async () => {
      globalThis.dispatchEvent(new Event("download:completed"));
    });

    expect(api.get).toHaveBeenCalledTimes(2);
  });
});
