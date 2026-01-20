import { describe, it, expect, vi, beforeEach } from "vitest";
import toast from "react-hot-toast";
import { notify } from "./notify";
import { useStore } from "../store/useStore";

// Mock react-hot-toast
vi.mock("react-hot-toast", () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
  }),
}));

// Mock the store
vi.mock("../store/useStore", () => ({
  useStore: {
    getState: vi.fn(() => ({
      addNotification: vi.fn(),
    })),
  },
}));

describe("notify", () => {
  const mockAddNotification = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore.getState as ReturnType<typeof vi.fn>).mockReturnValue({
      addNotification: mockAddNotification,
    });
  });

  describe("success", () => {
    it("should add notification to store and show toast", () => {
      notify.success("Operation successful");

      expect(mockAddNotification).toHaveBeenCalledWith(
        "success",
        "Operation successful",
      );
      expect(toast.success).toHaveBeenCalledWith("Operation successful");
    });
  });

  describe("error", () => {
    it("should add notification to store and show error toast", () => {
      notify.error("Something went wrong");

      expect(mockAddNotification).toHaveBeenCalledWith(
        "error",
        "Something went wrong",
      );
      expect(toast.error).toHaveBeenCalledWith("Something went wrong");
    });
  });

  describe("info", () => {
    it("should add notification to store and show info toast with icon", () => {
      notify.info("Information message");

      expect(mockAddNotification).toHaveBeenCalledWith(
        "info",
        "Information message",
      );
      expect(toast).toHaveBeenCalledWith("Information message", { icon: "ℹ️" });
    });
  });

  describe("warning", () => {
    it("should add notification to store and show warning toast with icon", () => {
      notify.warning("Warning message");

      expect(mockAddNotification).toHaveBeenCalledWith(
        "warning",
        "Warning message",
      );
      expect(toast).toHaveBeenCalledWith("Warning message", { icon: "⚠️" });
    });
  });

  describe("custom", () => {
    it("should expose the raw toast function", () => {
      expect(notify.custom).toBe(toast);
    });
  });
});
