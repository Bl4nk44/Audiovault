import { describe, it, expect, beforeEach, vi } from "vitest";
import { createAuthSlice, type AuthSlice } from "./authSlice";
import type { User } from "../../types";

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};

declare global {
  var localStorage: typeof localStorageMock;
}

Object.defineProperty(global, "localStorage", { value: localStorageMock });

describe("authSlice", () => {
  let state: AuthSlice;
  let set: (
    partial: Partial<AuthSlice> | ((state: AuthSlice) => Partial<AuthSlice>),
  ) => void;
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
    });

    it("should not be authenticated when no session exists", () => {
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
    it("should set user", () => {
      state.setUser(mockUser);

      expect(state.user).toEqual(mockUser);
    });

    it("should set user to null", () => {
      state.user = mockUser;

      state.setUser(null);

      expect(state.user).toBeNull();
    });
  });

  describe("setTokens", () => {
    it("should store tokens in localStorage", () => {
      state.setTokens(mockToken, mockRefreshToken);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "access_token",
        mockToken,
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "refresh_token",
        mockRefreshToken,
      );
    });

    it("should update state with tokens", () => {
      state.setTokens(mockToken, mockRefreshToken);

      expect(state.token).toBe(mockToken);
      expect(state.refreshToken).toBe(mockRefreshToken);
      expect(state.isAuthenticated).toBe(true);
    });

    it("should remove tokens from localStorage when null", () => {
      state.setTokens(null, null);

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("addSession", () => {
    it("should add session and set as current", () => {
      state.addSession(mockUser, mockToken, mockRefreshToken);

      expect(state.user).toEqual(mockUser);
      expect(state.token).toBe(mockToken);
      expect(state.isAuthenticated).toBe(true);
      expect(state.sessions["user-1"]).toBeDefined();
    });

    it("should store sessions in localStorage", () => {
      state.addSession(mockUser, mockToken, mockRefreshToken);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "sessions",
        expect.stringContaining("user-1"),
      );
    });
  });

  describe("switchSession", () => {
    it("should switch to another session", () => {
      const user2: User = {
        ...mockUser,
        id: "user-2",
        email: "user2@test.com",
      };
      state.sessions = {
        "user-1": {
          user: mockUser,
          token: mockToken,
          refreshToken: mockRefreshToken,
        },
        "user-2": { user: user2, token: "token-2", refreshToken: "refresh-2" },
      };
      state.user = mockUser;

      state.switchSession("user-2");

      expect(state.user).toEqual(user2);
      expect(state.token).toBe("token-2");
    });

    it("should not change state if session not found", () => {
      state.user = mockUser;
      state.sessions = {};

      state.switchSession("non-existent");

      expect(state.user).toEqual(mockUser);
    });
  });

  describe("removeSession", () => {
    it("should remove session from sessions object", () => {
      state.sessions = {
        "user-1": {
          user: mockUser,
          token: mockToken,
          refreshToken: mockRefreshToken,
        },
      };

      state.removeSession("user-1");

      expect(state.sessions["user-1"]).toBeUndefined();
    });

    it("should logout if removing current session", () => {
      state.user = mockUser;
      state.sessions = {
        "user-1": {
          user: mockUser,
          token: mockToken,
          refreshToken: mockRefreshToken,
        },
      };

      state.removeSession("user-1");

      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe("updateUserPreferences", () => {
    it("should update user preferences", () => {
      state.user = mockUser;
      state.sessions = {
        "user-1": {
          user: mockUser,
          token: mockToken,
          refreshToken: mockRefreshToken,
        },
      };

      state.updateUserPreferences({ theme: "light" });

      expect(state.user?.preferences.theme).toBe("light");
    });

    it("should not fail if no user logged in", () => {
      state.user = null;

      expect(() =>
        state.updateUserPreferences({ theme: "light" }),
      ).not.toThrow();
    });

    it("should update sessions in localStorage", () => {
      state.user = mockUser;
      state.sessions = {
        "user-1": {
          user: mockUser,
          token: mockToken,
          refreshToken: mockRefreshToken,
        },
      };

      state.updateUserPreferences({ language: "pl" });

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "sessions",
        expect.any(String),
      );
    });
  });

  describe("syncUser", () => {
    it("should sync user and update session", () => {
      state.token = mockToken;
      state.refreshToken = mockRefreshToken;
      state.sessions = {};

      state.syncUser(mockUser);

      expect(state.user).toEqual(mockUser);
      expect(state.sessions["user-1"]).toBeDefined();
    });

    it("should not sync if no tokens available", () => {
      state.token = null;
      state.refreshToken = null;

      state.syncUser(mockUser);

      expect(state.sessions["user-1"]).toBeUndefined();
    });
  });

  describe("logout", () => {
    it("should clear user and tokens", () => {
      state.user = mockUser;
      state.token = mockToken;
      state.refreshToken = mockRefreshToken;
      state.isAuthenticated = true;

      state.logout();

      expect(state.user).toBeNull();
      expect(state.token).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it("should remove tokens from localStorage", () => {
      state.user = mockUser;
      state.token = mockToken;

      state.logout();

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
    });
  });
});
