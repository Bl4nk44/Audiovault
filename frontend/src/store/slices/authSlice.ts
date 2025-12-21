import { type StateCreator } from "zustand";
import { type User } from "../../types";

export interface AuthSlice {
  user: User | null;
  isAuthenticated: boolean;
  token: string | null;
  refreshToken: string | null;
  sessions: Record<string, { user: User; token: string; refreshToken: string }>;
  setUser: (user: User | null) => void;
  setTokens: (accessToken: string | null, refreshToken: string | null) => void;
  addSession: (user: User, accessToken: string, refreshToken: string) => void;
  switchSession: (userId: string) => void;
  removeSession: (userId: string) => void;
  updateUserPreferences: (prefs: Record<string, unknown>) => void;
  logout: () => void;
}

export const createAuthSlice: StateCreator<AuthSlice> = (set, get) => {
  // Attempt to restore user from sessions based on active token
  const token = localStorage.getItem("access_token");
  const refreshToken = localStorage.getItem("refresh_token");
  const sessions = JSON.parse(
    localStorage.getItem("sessions") || "{}"
  ) as Record<string, { user: User; token: string; refreshToken: string }>;
  let user = null;

  if (token) {
    const session = Object.values(sessions).find(
      (s: { token: string }) => s.token === token
    ) as { user: User; token: string } | undefined;
    if (session) {
      user = session.user;
    }
  }

  return {
    user,
    isAuthenticated: !!token,
    token,
    refreshToken,
    sessions,

    setUser: (user) => set({ user }),

    setTokens: (accessToken, refreshToken) => {
      if (accessToken) {
        localStorage.setItem("access_token", accessToken);
      } else {
        localStorage.removeItem("access_token");
      }

      if (refreshToken) {
        localStorage.setItem("refresh_token", refreshToken);
      } else {
        localStorage.removeItem("refresh_token");
      }

      set({ token: accessToken, refreshToken, isAuthenticated: !!accessToken });
    },

    addSession: (user, accessToken, refreshToken) => {
      const sessions = {
        ...get().sessions,
        [user.id]: { user, token: accessToken, refreshToken },
      };
      localStorage.setItem("sessions", JSON.stringify(sessions));

      // Also set as current
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      set({
        sessions,
        user,
        token: accessToken,
        refreshToken,
        isAuthenticated: true,
      });
    },

    switchSession: (userId) => {
      const session = get().sessions[userId];
      if (session) {
        localStorage.setItem("access_token", session.token);
        localStorage.setItem("refresh_token", session.refreshToken);
        set({
          user: session.user,
          token: session.token,
          refreshToken: session.refreshToken,
          isAuthenticated: true,
        });
        window.location.reload(); // Reload to refresh state/sockets
      }
    },

    removeSession: (userId) => {
      const sessions = { ...get().sessions };
      delete sessions[userId];
      localStorage.setItem("sessions", JSON.stringify(sessions));
      set({ sessions });

      // If removing current session, logout
      if (get().user?.id === userId) {
        get().logout();
      }
    },

    updateUserPreferences: (prefs: Record<string, unknown>) => {
      const user = get().user;
      if (user) {
        const updatedUser = {
          ...user,
          preferences: { ...user.preferences, ...prefs },
        };
        set({ user: updatedUser });

        // Also update session in localStorage
        const sessions = { ...get().sessions };
        if (sessions[user.id]) {
          sessions[user.id].user = updatedUser;
          localStorage.setItem("sessions", JSON.stringify(sessions));
        }
      }
    },

    logout: () => {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      set({
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
      });
    },
  };
};
