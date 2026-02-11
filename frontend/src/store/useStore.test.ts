import { beforeEach, describe, expect, it } from "vitest";
import { useStore } from "./useStore";

describe("useStore", () => {
  beforeEach(() => {
    const { logout, clearNotifications } = useStore.getState();
    logout();
    clearNotifications();
  });

  it("should initialize with all combined slices", () => {
    const state = useStore.getState();

    // Check if properties from different slices exist
    expect(state).toHaveProperty("user"); // from authSlice
    expect(state).toHaveProperty("isPlaying"); // from playerSlice
    expect(state).toHaveProperty("queue"); // from queueSlice
    expect(state).toHaveProperty("watchlist"); // from watchlistSlice
    expect(state).toHaveProperty("notifications"); // from notificationSlice
  });

  it("should allow updating state via actions from slices", () => {
    const { addNotification } = useStore.getState();

    // Correct arguments order: type, message
    addNotification("success", "Test Notification");

    const state = useStore.getState();
    expect(state.notifications).toHaveLength(1);
    expect(state.notifications[0].message).toBe("Test Notification");
  });
});
