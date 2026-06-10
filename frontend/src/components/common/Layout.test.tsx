import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../../services/api";
import Layout from "./Layout";

const mockAddNotification = vi.fn();

vi.mock("../../services/api");
vi.mock("../../hooks/useSocketEvents", () => ({
  useSocketEvents: vi.fn(),
}));
vi.mock("../../store/useStore", () => ({
  useStore: () => ({ addNotification: mockAddNotification }),
}));

// Mock child components to avoid deep rendering issues and focus on Layout logic
vi.mock("./Sidebar", () => ({ default: () => <div data-testid="sidebar">Sidebar</div> }));
vi.mock("./Navbar", () => ({ default: () => <div data-testid="navbar">Navbar</div> }));
vi.mock("./MobileNav", () => ({ default: () => <div data-testid="mobile-nav">MobileNav</div> }));
vi.mock("./DownloadNotifications", () => ({
  default: () => <div data-testid="download-notifications">Notifications</div>,
}));
vi.mock("../player/Player", () => ({ default: () => <div data-testid="player">Player</div> }));

describe("Layout Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockResolvedValue({ data: { update_available: false } });
  });

  const renderLayout = () => {
    return render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    );
  };

  it("renders main structure components", () => {
    renderLayout();

    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("navbar")).toBeInTheDocument();
    expect(screen.getByTestId("player")).toBeInTheDocument();
    expect(screen.getByTestId("mobile-nav")).toBeInTheDocument();
    expect(screen.getByTestId("download-notifications")).toBeInTheDocument();
  });

  it("checks for updates on mount", async () => {
    renderLayout();

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/system/check-update");
    });
  });

  it("does not notify if no update available", async () => {
    renderLayout();

    await waitFor(() => {
      expect(api.get).toHaveBeenCalled();
    });

    expect(mockAddNotification).not.toHaveBeenCalled();
  });

  it("adds notification if update available", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        update_available: true,
        latest_version: "1.0.1",
        release_url: "http://github.com",
      },
    });

    renderLayout();

    await waitFor(() => {
      expect(mockAddNotification).toHaveBeenCalledWith("info", expect.any(String));
    });
  });
});
