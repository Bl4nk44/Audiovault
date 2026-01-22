import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../../services/api";
import SystemStats from "./SystemStats";

// Mock the API module
vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

describe("SystemStats Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton initially", () => {
    // Mock a promise that doesn't resolve immediately to check loading state
    (api.get as any).mockImplementation(() => new Promise(() => {}));

    render(<SystemStats />);
    // Check for the skeleton structure (using class names or structural assumptions if no text)
    // The skeleton has "animate-pulse" class
    // We can just check if "System Status" title is NOT present yet if it only renders after data
    // The component code shows "System Status" is inside the main block, effectively only after stats are loaded?
    // Looking at code: "if (!stats) return ... skeleton ..."
    // So "System Status" text should NOT be there.

    expect(screen.queryByText("System Status")).not.toBeInTheDocument();
  });

  it("renders stats data correctly after fetching", async () => {
    const mockStats = {
      cpu: { percent: 45.5 },
      memory: { total: 16000000000, used: 8000000000, percent: 50.0 },
      disk: { total: 500000000000, used: 250000000000, percent: 50.0 },
      network: { sent: 1024, recv: 2048 },
    };

    (api.get as any).mockResolvedValue({ data: mockStats });

    render(<SystemStats />);

    // Wait for the data to be rendered using findByText for the header
    expect(await screen.findByText("System Status")).toBeInTheDocument();

    // Check CPU (Gauge rounds the value)
    expect(screen.getByText(/46/)).toBeInTheDocument();

    // Check text for CPU label
    expect(screen.getByText("CPU Load")).toBeInTheDocument();
    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("Storage")).toBeInTheDocument();
    expect(screen.getByText("Network Total")).toBeInTheDocument();
  });

  it("handles API error gracefully", async () => {
    // Mock API error
    const consoleSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    (api.get as any).mockRejectedValue(new Error("API Error"));

    render(<SystemStats />);

    // Should stay in loading state or render nothing/error?
    // Code catches error and logs it. current state 'stats' remains null.
    // So it should show skeleton.

    await waitFor(() => {
      expect(api.get).toHaveBeenCalled();
    });

    expect(screen.queryByText("System Status")).not.toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
