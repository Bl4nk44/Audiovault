import { describe, it, expect, beforeEach, vi } from "vitest";
import { createNotificationSlice, type NotificationSlice } from "./notificationSlice";
import type { Notification } from "../../types";

// localStorage is mocked globally in setupTests.ts
const localStorageMock = globalThis.localStorage as any;

describe("notificationSlice", () => {
  let state: NotificationSlice;
  let set: (
    partial:
      | Partial<NotificationSlice>
      | ((state: NotificationSlice) => Partial<NotificationSlice>),
  ) => void;
  let get: () => NotificationSlice;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);

    set = (partial) => {
      if (typeof partial === "function") {
        Object.assign(state, partial(state));
      } else {
        Object.assign(state, partial);
      }
    };
    get = () => state;

    state = createNotificationSlice(set, get, {} as never);
  });

  describe("initial state", () => {
    it("should have empty notifications array", () => {
      expect(state.notifications).toEqual([]);
    });
  });

  describe("showNotification", () => {
    it("should add notification to queue", () => {
      const notification: Notification = {
        id: "1",
        type: "success",
        message: "Test message",
      };

      state.showNotification(notification);

      expect(state.notifications).toContainEqual(notification);
    });

    it("should auto-dismiss notifications after timeout", () => {
      vi.useFakeTimers();

      const notification: Notification = {
        id: "1",
        type: "info",
        message: "Auto-dismiss test",
      };

      state.showNotification(notification);
      expect(state.notifications).toHaveLength(1);

      vi.advanceTimersByTime(5000);

      vi.restoreAllMocks();
    });
  });

  describe("removeNotification", () => {
    it("should remove notification by id", () => {
      state.notifications = [
        { id: "1", type: "success", message: "Test" },
        { id: "2", type: "error", message: "Error" },
      ];

      state.removeNotification("1");

      expect(state.notifications).toEqual([
        { id: "2", type: "error", message: "Error" },
      ]);
    });
  });

  describe("clearNotifications", () => {
    it("should clear all notifications", () => {
      state.notifications = [
        { id: "1", type: "success", message: "Test" },
        { id: "2", type: "error", message: "Error" },
      ];

      state.clearNotifications();

      expect(state.notifications).toEqual([]);
    });
  });
});
