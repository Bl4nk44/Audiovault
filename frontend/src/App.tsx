import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Search from "./pages/Search";
import Queue from "./pages/Queue";
import Watchlist from "./pages/Watchlist";
import Library from "./pages/Library";
import Settings from "./pages/Settings";

import ArtistProfile from "./pages/ArtistProfile";
import Import from "./pages/Import";
import NotFound from "./pages/NotFound";
import Layout from "./components/common/Layout";
import { useStore } from "./store/useStore";

import React from "react";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useStore((state) => state.isAuthenticated);
  return isAuthenticated ? children : <Navigate to="/login" />;
}

function ThemeInit() {
  const user = useStore((state) => state.user);

  React.useLayoutEffect(() => {
    let theme = user?.preferences?.theme;

    // Fallback to localStorage if user state not ready
    if (!theme) {
      try {
        const stored = localStorage.getItem("sessions");
        if (stored) {
          const sessions = JSON.parse(stored);
          const currentToken = localStorage.getItem("access_token");
          if (currentToken) {
            // Define minimal interface for legacy session parsing
            interface SessionData {
              user?: { preferences?: { theme?: string } };
            }
            const session = Object.values(sessions).find(
              (s: unknown) => (s as any).token === currentToken
            ) as SessionData | undefined;
            if (session?.user?.preferences?.theme) {
              theme = session.user.preferences.theme;
            }
          }
        }
      } catch {
        // Ignore parsing errors
      }
    }

    // specific fallback: if still no theme, check if 'classic' was previously set (legacy) and default to 'dark'
    // otherwise use 'dark' as safe default
    if (!theme) theme = "dark";

    document.documentElement.className = theme;
  }, [user?.preferences?.theme]);

  // Handle immediate application on mount to ensure sync
  React.useLayoutEffect(() => {
    const savedClass = document.documentElement.className;
    if (user?.preferences?.theme && savedClass !== user.preferences.theme) {
      document.documentElement.className = user.preferences.theme;
    }
  }, [user]);

  return null;
}

function SessionManager() {
  const isAuthenticated = useStore((state) => state.isAuthenticated);
  const syncUser = useStore((state) => state.syncUser);

  React.useEffect(() => {
    if (isAuthenticated) {
      // Dynamic import to avoid circular dependency in some bundler setups,
      // though here it's mainly to keep it cleanly separated or ensuring api is ready.
      import("./services/api").then(({ default: api }) => {
        api
          .get("/users/me")
          .then((res) => {
            if (res.data) {
              syncUser(res.data);
            }
          })
          .catch((err) => {
            console.error("Failed to restore session user data:", err);
            // If 401, the interceptor will handle logout.
          });
      });
    }
  }, [isAuthenticated, syncUser]);

  return null;
}

function App() {
  return (
    <Router>
      <ThemeInit />
      <SessionManager />
      <div className="min-h-screen text-foreground font-sans antialiased relative">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="search" element={<Search />} />
            <Route path="queue" element={<Queue />} />
            <Route path="watchlist" element={<Watchlist />} />
            <Route path="library" element={<Library />} />

            <Route path="settings" element={<Settings />} />

            <Route path="artist/:id" element={<ArtistProfile />} />
            <Route path="import" element={<Import />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "hsl(var(--card))",
              color: "hsl(var(--foreground))",
              border: "1px solid hsl(var(--border))",
            },
          }}
        />
      </div>
    </Router>
  );
}

export default App;
