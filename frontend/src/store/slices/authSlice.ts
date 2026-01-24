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
  syncUser: (user: User) => void;
  logout: () => void;
}

export const createAuthSlice: StateCreator<AuthSlice> = (set, get) => {
  // Attempt to restore user from sessions based on active token
  const token = localStorage.getItem("access_token");
  const refreshToken = localStorage.getItem("refresh_token");
  const sessions = JSON.parse(localStorage.getItem("sessions") || "{}") as Record<
    string,
    { user: User; token: string; refreshToken: string }
  >;
  let user = null;

  if (token) {
    // deepcode ignore ObservableTimingDiscrepancy: Client-side token comparison
    const session = Object.values(sessions).find((s: { token: string }) => s.token === token) as
      | { user: User; token: string }
      | undefined;
    if (session) {
      user = session.user;
    }
  }

  return {
    user,
    isAuthenticated: !!user, // Only authenticated if we successfully restored a user session
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
        globalThis.location.reload(); // Reload to refresh state/sockets
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
        // We use a type assertion here because merging partial unknown preferences
        // requires validation in a real app.
        const updatedUser = {
          ...user,
          preferences: {
            ...user.preferences,
            ...prefs,
          } as unknown as User["preferences"],
        };
        set({ user: updatedUser });

        // Update user in sessions
        const userId = user.id;
        const sessions = { ...get().sessions };

        if (sessions[userId]) {
          sessions[userId].user = updatedUser;
          localStorage.setItem("sessions", JSON.stringify(sessions));
          set({ sessions });
        }
      }
    },

    syncUser: (user: User) => {
      // Get current tokens (either from state or storage if state empty due to reload)
      const token = get().token || localStorage.getItem("access_token");
      const refreshToken = get().refreshToken || localStorage.getItem("refresh_token");

      if (token && refreshToken) {
        set({ user });

        const sessions = {
          ...get().sessions,
          [user.id]: { user, token, refreshToken },
        };

        localStorage.setItem("sessions", JSON.stringify(sessions));
        set({ sessions });
      }
    },

    checkAuth: async () => {
      const token = localStorage.getItem("access_token");
      if (!token) return;

      try {
        // Dynamic import to avoid circular dependency if api depends on store
        const { default: api } = await import("../../services/api");
        const response = await api.get<User>("/auth/me");
        set({ user: response.data, isAuthenticated: true });

        // Update session info if needed
        const sessions = { ...get().sessions };
        if (response.data.id && sessions[response.data.id]) {
          sessions[response.data.id].user = response.data;
          localStorage.setItem("sessions", JSON.stringify(sessions));
          set({ sessions });
        }
      } catch (error) {
        console.error("Token verification failed", error);
        get().logout();
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
