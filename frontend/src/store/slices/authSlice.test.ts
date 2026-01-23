import { beforeEach, describe, expect, it, Mock, vi } from "vitest";
import type { User } from "../../types";
import { createAuthSlice, type AuthSlice } from "./authSlice";

// localStorage is mocked globally in setupTests.ts
const localStorageMock = globalThis.localStorage as any;

// Mock api service
vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

// Mock global location reload
const originalLocation = globalThis.location;
// @ts-ignore
delete globalThis.location;
globalThis.location = { ...originalLocation, reload: vi.fn() } as any;

import api from "../../services/api";

describe("authSlice", () => {
  let state: AuthSlice;
  let set: (partial: Partial<AuthSlice> | ((state: AuthSlice) => Partial<AuthSlice>)) => void;
  let get: () => AuthSlice;

  const mockUser: User = {
    id: "user-1",
    email: "test@example.com",
    username: "testuser",
    preferences: {
      theme: "dark",
      language: "en",
    },
  };

  const mockToken = "mock-access-token";
  const mockRefreshToken = "mock-refresh-token";

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

    state = createAuthSlice(set, get, {} as never);
  });

  describe("initial state", () => {
    it("should have null user when no session exists", () => {
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it("should restore user from sessions if token matches", () => {
      const sessions = {
        "user-1": {
          user: mockUser,
          token: mockToken,
          refreshToken: mockRefreshToken,
        },
      };
      localStorageMock.getItem.mockImplementation((key: string) => {
        if (key === "access_token") return mockToken;
        if (key === "refresh_token") return mockRefreshToken;
        if (key === "sessions") return JSON.stringify(sessions);
        return null;
      });

      state = createAuthSlice(set, get, {} as never);

      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe("setUser", () => {
    it("should set user manually", () => {
      state.setUser(mockUser);
      expect(state.user).toEqual(mockUser);
    });
  });

  describe("setTokens", () => {
    it("should store tokens and update state", () => {
      state.setTokens(mockToken, mockRefreshToken);

      expect(localStorageMock.setItem).toHaveBeenCalledWith("access_token", mockToken);
      expect(localStorageMock.setItem).toHaveBeenCalledWith("refresh_token", mockRefreshToken);
      expect(state.token).toBe(mockToken);
      expect(state.isAuthenticated).toBe(true);
    });

    it("should clear tokens when null provided", () => {
      state.setTokens(null, null);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("addSession", () => {
    it("should add a new session and save to storage", () => {
      state.addSession(mockUser, mockToken, mockRefreshToken);
      expect(state.sessions[mockUser.id]).toBeDefined();
      expect(localStorageMock.setItem).toHaveBeenCalledWith("sessions", expect.any(String));
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe("switchSession", () => {
    it("should switch between existing sessions and reload", () => {
      const user2 = { ...mockUser, id: "user-2" };
      state.sessions = {
        "user-1": { user: mockUser, token: mockToken, refreshToken: mockRefreshToken },
        "user-2": { user: user2, token: "t2", refreshToken: "r2" },
      };

      state.switchSession("user-2");

      expect(localStorageMock.setItem).toHaveBeenCalledWith("access_token", "t2");
      expect(state.user?.id).toBe("user-2");
      expect(globalThis.location.reload).toHaveBeenCalled();
    });

    it("should not reload if session doesn't exist", () => {
      state.switchSession("invalid");
      expect(globalThis.location.reload).not.toHaveBeenCalled();
    });
  });

  describe("updateUserPreferences", () => {
    it("should merge preferences and update session storage", () => {
      state.user = mockUser;
      state.sessions = {
        [mockUser.id]: { user: mockUser, token: mockToken, refreshToken: mockRefreshToken },
      };

      state.updateUserPreferences({ theme: "light" });

      expect(state.user?.preferences.theme).toBe("light");
      expect(state.sessions[mockUser.id].user.preferences.theme).toBe("light");
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "sessions",
        expect.stringContaining("light")
      );
    });

    it("should do nothing if no user logged in", () => {
      state.user = null;
      state.updateUserPreferences({ theme: "light" });
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  describe("checkAuth", () => {
    it("should verify token and update user", async () => {
      localStorageMock.getItem.mockReturnValue(mockToken);
      (api.get as Mock).mockResolvedValue({ data: mockUser });

      await (state as any).checkAuth();

      expect(api.get).toHaveBeenCalledWith("/auth/me");
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });

    it("should logout on verification failure", async () => {
      localStorageMock.getItem.mockReturnValue(mockToken);
      (api.get as Mock).mockRejectedValue(new Error("Unauthorized"));
      const logoutSpy = vi.spyOn(state, "logout");

      await (state as any).checkAuth();

      expect(logoutSpy).toHaveBeenCalled();
    });
  });

  describe("removeSession", () => {
    it("should logout if current active user session is removed", () => {
      state.user = mockUser;
      state.sessions = {
        [mockUser.id]: { user: mockUser, token: mockToken, refreshToken: mockRefreshToken },
      };
      const logoutSpy = vi.spyOn(state, "logout");

      state.removeSession(mockUser.id);

      expect(logoutSpy).toHaveBeenCalled();
      expect(state.sessions[mockUser.id]).toBeUndefined();
    });

    it("should just remove from sessions if not active user", () => {
      state.user = { id: "active" } as any;
      state.sessions = { other: { user: { id: "other" } as any, token: "t", refreshToken: "r" } };
      const logoutSpy = vi.spyOn(state, "logout");

      state.removeSession("other");

      expect(logoutSpy).not.toHaveBeenCalled();
      expect(state.sessions["other"]).toBeUndefined();
    });
  });

  describe("syncUser", () => {
    it("should update sessions when syncing user data", () => {
      state.token = mockToken;
      state.refreshToken = mockRefreshToken;
      state.syncUser(mockUser);

      expect(state.sessions[mockUser.id]).toBeDefined();
      expect(state.sessions[mockUser.id].user).toEqual(mockUser);
    });
  });
});
