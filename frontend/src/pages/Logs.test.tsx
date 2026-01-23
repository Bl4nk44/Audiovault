import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import api from "../services/api";
import Logs from "./Logs";

// Mock dependencies
vi.mock("../services/api");
vi.mock("../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Safer framer-motion mock
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children }: any) => <div>{children}</div>,
  },
}));

describe("Logs Page (History)", () => {
  const sampleLogs = [
    "2023-01-01 12:00:00 [INFO] System started",
    "2023-01-01 12:01:00 [WARNING] Disk space low",
    "2023-01-01 12:02:00 [ERROR] Connection failed",
    "2023-01-01 12:03:00 [DEBUG] Variable x=1",
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    (api.get as unknown as Mock).mockResolvedValue({ data: [] });
    globalThis.URL.createObjectURL = vi.fn(() => "blob:url");
  });

  it("renders logs and fetches data on mount", async () => {
    (api.get as unknown as Mock).mockResolvedValue({ data: sampleLogs });
    render(<Logs />);
    await waitFor(() => {
      expect(screen.getByText("logs.title")).toBeInTheDocument();
      expect(screen.getByText(/System started/)).toBeInTheDocument();
      expect(screen.getAllByText(/2023-01-01/).length).toBe(4);
    });
  });

  it("filters logs to show errors only", async () => {
    (api.get as unknown as Mock).mockResolvedValue({ data: sampleLogs });
    render(<Logs />);
    await waitFor(() => expect(screen.getByText(/System started/)).toBeInTheDocument());

    const filterBtn = screen.getByText("logs.showErrorsOnly");
    fireEvent.click(filterBtn);

    await waitFor(() => {
      expect(screen.queryByText(/System started/)).not.toBeInTheDocument();
      expect(screen.getByText(/Connection failed/)).toBeInTheDocument();
    });

    fireEvent.click(filterBtn);
    await waitFor(() => expect(screen.getByText(/System started/)).toBeInTheDocument());
  });

  it("handles auto-refresh toggle", async () => {
    vi.useFakeTimers();
    (api.get as unknown as Mock).mockResolvedValue({ data: ["Log 1"] });

    render(<Logs />);
    // Initial fetch
    await act(async () => {
      await Promise.resolve(); // Flush mount effect
    });
    expect(api.get).toHaveBeenCalledTimes(1);

    // Advance 2.1s -> 2nd call
    await act(async () => {
      vi.advanceTimersByTime(2100);
    });
    expect(api.get).toHaveBeenCalledTimes(2);

    // Toggle OFF
    const refreshBtn = screen.getByText("logs.autoRefresh");
    fireEvent.click(refreshBtn);

    // Advance 3s -> Should NOT call again
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    // Flush promises
    await act(async () => {
      await Promise.resolve();
    });

    expect(api.get).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  }, 15000);

  it("handles manual refresh", async () => {
    (api.get as unknown as Mock).mockResolvedValue({ data: ["Log 1"] });
    render(<Logs />);
    await waitFor(() => expect(screen.getByText("Log 1")).toBeInTheDocument());

    const toggleAuto = screen.getByText("logs.autoRefresh");
    fireEvent.click(toggleAuto);

    const refreshBtn = screen.getByText("logs.refresh");
    fireEvent.click(refreshBtn);

    await waitFor(() => expect(api.get).toHaveBeenCalledTimes(2));
  });

  it("clears logs locally", async () => {
    (api.get as unknown as Mock).mockResolvedValue({ data: sampleLogs });
    render(<Logs />);
    await waitFor(() => expect(screen.getByText(/System started/)).toBeInTheDocument());

    const toggleAuto = screen.getByText("logs.autoRefresh");
    fireEvent.click(toggleAuto);

    const clearBtn = screen.getByText("logs.clear");
    fireEvent.click(clearBtn);

    await waitFor(() => {
      expect(screen.queryByText(/System started/)).not.toBeInTheDocument();
      expect(screen.getByText("No logs available...")).toBeInTheDocument();
    });
  });

  it("handles log download", async () => {
    render(<Logs />);
    const downloadBtn = screen.getByText("logs.download");

    (api.get as unknown as Mock).mockImplementation((url) => {
      if (url.includes("download")) return Promise.resolve({ data: "log content" });
      return Promise.resolve({ data: [] });
    });

    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/system/logs/download",
        expect.objectContaining({ responseType: "blob" })
      );
      expect(globalThis.URL.createObjectURL).toHaveBeenCalled();
    });
  });
});
