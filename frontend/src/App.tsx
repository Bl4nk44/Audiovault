import { Toaster } from "react-hot-toast";
import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Library from "./pages/Library";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import Queue from "./pages/Queue";
import Register from "./pages/Register";
import Search from "./pages/Search";
import Settings from "./pages/Settings";
import Watchlist from "./pages/Watchlist";

import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import Layout from "./components/common/Layout";
import { SessionManager } from "./components/common/SessionManager";
import { ThemeInitializer } from "./components/common/ThemeInitializer";
import { AnimatedBackground } from "./components/ui/AnimatedBackground";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import AlbumDetails from "./pages/AlbumDetails";
import ArtistProfile from "./pages/ArtistProfile";
import Import from "./pages/Import";
import NotFound from "./pages/NotFound";
import PlaylistDetails from "./pages/PlaylistDetails";

function App() {
  return (
    <Router>
      <ThemeInitWrapper />
      <SessionManagerWrapper />
      <KeyboardShortcutsWrapper />
      <div className="min-h-screen text-foreground relative overflow-hidden font-sans selection:bg-primary/30 selection:text-primary-foreground">
        <AnimatedBackground />
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
            <Route path="album/:id" element={<AlbumDetails />} />
            <Route path="playlist/:id" element={<PlaylistDetails />} />
            <Route path="import" element={<Import />} />
            <Route path="logs" element={<Logs />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "hsl(var(--card) / 0.8)",
              backdropFilter: "blur(12px)",
              color: "hsl(var(--foreground))",
              border: "1px solid hsl(var(--border))",
            },
          }}
        />
      </div>
    </Router>
  );
}

// Simple wrappers to avoid 'children' type issues if any, or just direct usage
function ThemeInitWrapper() {
  return <ThemeInitializer />;
}

function SessionManagerWrapper() {
  return <SessionManager />;
}

function KeyboardShortcutsWrapper() {
  useKeyboardShortcuts();
  return null;
}

export default App;
