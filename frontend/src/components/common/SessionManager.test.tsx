import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useStore } from "../../store/useStore";
import { SessionManager } from "./SessionManager";

// Mock store
vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

// Mock API module for dynamic import
const mockApiGet = vi.fn();
vi.mock("../../services/api", () => ({
  default: {
    get: mockApiGet,
  },
}));

describe("SessionManager", () => {
  const mockSyncUser = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should not fetch user if not authenticated", () => {
    (useStore as unknown as Mock).mockImplementation((selector) =>
      selector({ isAuthenticated: false, syncUser: mockSyncUser })
    );

    render(<SessionManager />);
    expect(mockApiGet).not.toHaveBeenCalled();
  });

  it("should fetch user and sync if authenticated", async () => {
    (useStore as unknown as Mock).mockImplementation((selector) =>
      selector({ isAuthenticated: true, syncUser: mockSyncUser })
    );
    mockApiGet.mockResolvedValue({ data: { id: "u1", username: "test" } });

    render(<SessionManager />);

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith("/users/me");
      expect(mockSyncUser).toHaveBeenCalledWith({ id: "u1", username: "test" });
    });
  });

  it("should handle fetch error gracefully", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    (useStore as unknown as Mock).mockImplementation((selector) =>
      selector({ isAuthenticated: true, syncUser: mockSyncUser })
    );
    mockApiGet.mockRejectedValue(new Error("API Error"));

    render(<SessionManager />);

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalled();
      expect(consoleSpy).toHaveBeenCalledWith(
        "Failed to restore session user data:",
        expect.any(Error)
      );
    });
    consoleSpy.mockRestore();
  });
});
