import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../../services/api";
import Layout from "./Layout";

// Mock dependencies
vi.mock("../../services/api");
vi.mock("../../hooks/useSocketEvents", () => ({
  useSocketEvents: vi.fn(),
}));

vi.mock("react-hot-toast", () => ({
  default: vi.fn(),
}));

// Mock child components to avoid deep rendering issues and focus on Layout logic
vi.mock("./Sidebar", () => ({ default: () => <div data-testid="sidebar">Sidebar</div> }));
vi.mock("./Navbar", () => ({ default: () => <div data-testid="navbar">Navbar</div> }));
vi.mock("./MobileNav", () => ({ default: () => <div data-testid="mobile-nav">MobileNav</div> }));
vi.mock("./DownloadNotifications", () => ({
  default: () => <div data-testid="download-notifications">Notifications</div>,
}));
vi.mock("../player/Player", () => ({ default: () => <div data-testid="player">Player</div> }));
vi.mock("./UpdateToast", () => ({ UpdateToast: () => <div>Toast</div> }));

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

  it("does not toast if no update available", async () => {
    renderLayout();

    await waitFor(() => {
      expect(api.get).toHaveBeenCalled();
    });

    const toast = await import("react-hot-toast");
    expect(toast.default).not.toHaveBeenCalled();
  });

  it("shows toast if update available", async () => {
    (api.get as any).mockResolvedValue({
      data: {
        update_available: true,
        latest_version: "1.0.1",
        release_url: "http://github.com",
      },
    });

    renderLayout();

    await waitFor(() => {
      expect(api.get).toHaveBeenCalled();
    });

    const toast = await import("react-hot-toast");
    expect(toast.default).toHaveBeenCalled();
  });
});
