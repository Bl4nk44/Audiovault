import { describe, it, expect, beforeEach } from "vitest";
import {
  createNotificationSlice,
  type NotificationSlice,
} from "./notificationSlice";

describe("notificationSlice", () => {
  let state: NotificationSlice;
  let set: (
    partial:
      | Partial<NotificationSlice>
      | ((state: NotificationSlice) => Partial<NotificationSlice>),
  ) => void;

  beforeEach(() => {
    // Create a simple mock for set function
    set = (partial) => {
      if (typeof partial === "function") {
        Object.assign(state, partial(state));
      } else {
        Object.assign(state, partial);
      }
    };

    // Initialize fresh state for each test
    state = createNotificationSlice(set, () => state, {} as never);
  });

  describe("initial state", () => {
    it("should have empty notifications array", () => {
      expect(state.notifications).toEqual([]);
    });

    it("should have unreadCount of 0", () => {
      expect(state.unreadCount).toBe(0);
    });
  });

  describe("addNotification", () => {
    it("should add a new notification to the beginning of the array", () => {
      state.addNotification("success", "Test message");

      expect(state.notifications).toHaveLength(1);
      expect(state.notifications[0].message).toBe("Test message");
      expect(state.notifications[0].type).toBe("success");
      expect(state.notifications[0].read).toBe(false);
    });

    it("should increment unreadCount when adding notification", () => {
      state.addNotification("info", "Info message");

      expect(state.unreadCount).toBe(1);
    });

    it("should add notifications in reverse chronological order", () => {
      state.addNotification("success", "First");
      state.addNotification("error", "Second");

      expect(state.notifications[0].message).toBe("Second");
      expect(state.notifications[1].message).toBe("First");
    });

    it("should generate unique IDs for each notification", () => {
      state.addNotification("info", "First");
      state.addNotification("info", "Second");

      expect(state.notifications[0].id).not.toBe(state.notifications[1].id);
    });

    it("should set timestamp on notification", () => {
      const before = Date.now();
      state.addNotification("warning", "Test");
      const after = Date.now();

      expect(state.notifications[0].timestamp).toBeGreaterThanOrEqual(before);
      expect(state.notifications[0].timestamp).toBeLessThanOrEqual(after);
    });
  });

  describe("markAsRead", () => {
    it("should mark a specific notification as read", () => {
      state.addNotification("success", "Test");
      const notificationId = state.notifications[0].id;

      state.markAsRead(notificationId);

      expect(state.notifications[0].read).toBe(true);
    });

    it("should update unreadCount when marking as read", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");
      expect(state.unreadCount).toBe(2);

      state.markAsRead(state.notifications[0].id);

      expect(state.unreadCount).toBe(1);
    });

    it("should not affect other notifications", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");

      state.markAsRead(state.notifications[0].id);

      expect(state.notifications[0].read).toBe(true);
      expect(state.notifications[1].read).toBe(false);
    });
  });

  describe("markAllAsRead", () => {
    it("should mark all notifications as read", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");
      state.addNotification("info", "Test 3");

      state.markAllAsRead();

      expect(state.notifications.every((n) => n.read)).toBe(true);
    });

    it("should set unreadCount to 0", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");

      state.markAllAsRead();

      expect(state.unreadCount).toBe(0);
    });
  });

  describe("clearNotifications", () => {
    it("should remove all notifications", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");

      state.clearNotifications();

      expect(state.notifications).toEqual([]);
    });

    it("should reset unreadCount to 0", () => {
      state.addNotification("success", "Test 1");

      state.clearNotifications();

      expect(state.unreadCount).toBe(0);
    });
  });

  describe("removeNotification", () => {
    it("should remove a specific notification by id", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");
      const idToRemove = state.notifications[0].id;

      state.removeNotification(idToRemove);

      expect(state.notifications).toHaveLength(1);
      expect(state.notifications[0].message).toBe("Test 1");
    });

    it("should update unreadCount when removing unread notification", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");
      expect(state.unreadCount).toBe(2);

      state.removeNotification(state.notifications[0].id);

      expect(state.unreadCount).toBe(1);
    });

    it("should not change unreadCount when removing read notification", () => {
      state.addNotification("success", "Test 1");
      state.addNotification("error", "Test 2");
      state.markAsRead(state.notifications[0].id);
      expect(state.unreadCount).toBe(1);

      state.removeNotification(state.notifications[0].id);

      expect(state.unreadCount).toBe(1);
    });
  });
});
