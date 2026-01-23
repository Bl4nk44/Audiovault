import { beforeEach, describe, expect, it, vi } from "vitest";
import { createNotificationSlice, type NotificationSlice } from "./notificationSlice";

// localStorage is mocked globally in setupTests.ts
const localStorageMock = globalThis.localStorage as any;

describe("notificationSlice", () => {
  let state: NotificationSlice;
  let set: (
    partial: Partial<NotificationSlice> | ((state: NotificationSlice) => Partial<NotificationSlice>)
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
    it("should have empty notifications array and zero unread count", () => {
      expect(state.notifications).toEqual([]);
      expect(state.unreadCount).toBe(0);
    });
  });

  describe("addNotification", () => {
    it("should add notification and increment unread count", () => {
      state.addNotification("success", "Test message");

      expect(state.notifications).toHaveLength(1);
      expect(state.notifications[0].message).toBe("Test message");
      expect(state.notifications[0].read).toBe(false);
      expect(state.unreadCount).toBe(1);
    });

    it("should add multiple notifications in correct order", () => {
      state.addNotification("info", "First");
      state.addNotification("warning", "Second");

      expect(state.notifications[0].message).toBe("Second");
      expect(state.notifications[1].message).toBe("First");
      expect(state.unreadCount).toBe(2);
    });
  });

  describe("marking as read", () => {
    beforeEach(() => {
      state.addNotification("info", "N1");
      state.addNotification("error", "N2");
    });

    it("markAsRead should set read flag and update unread count", () => {
      const id = state.notifications[0].id;
      state.markAsRead(id);

      expect(state.notifications[0].read).toBe(true);
      expect(state.unreadCount).toBe(1);
    });

    it("markAllAsRead should clear unread count", () => {
      state.markAllAsRead();
      expect(state.notifications.every((n) => n.read)).toBe(true);
      expect(state.unreadCount).toBe(0);
    });
  });

  describe("removeNotification", () => {
    it("should remove notification and update unread count if it was unread", () => {
      state.addNotification("success", "T1");
      const id = state.notifications[0].id;

      state.removeNotification(id);

      expect(state.notifications).toHaveLength(0);
      expect(state.unreadCount).toBe(0);
    });
  });

  describe("clearNotifications", () => {
    it("should clear all notifications and reset unread count", () => {
      state.addNotification("success", "T1");
      state.clearNotifications();

      expect(state.notifications).toEqual([]);
      expect(state.unreadCount).toBe(0);
    });
  });
});
