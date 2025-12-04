import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Search from './pages/Search'
import Queue from './pages/Queue'
import Watchlist from './pages/Watchlist'
import Library from './pages/Library'
import Settings from './pages/Settings'
import CreatePlaylist from './pages/CreatePlaylist'
import LikedSongs from './pages/LikedSongs'
import NotFound from './pages/NotFound'
import Layout from './components/common/Layout'
import { useStore } from './store/useStore'

import React from 'react'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useStore((state) => state.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/login" />
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background text-foreground font-sans antialiased">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<Dashboard />} />
            <Route path="search" element={<Search />} />
            <Route path="queue" element={<Queue />} />
            <Route path="watchlist" element={<Watchlist />} />
            <Route path="library" element={<Library />} />
            <Route path="settings" element={<Settings />} />
            <Route path="create-playlist" element={<CreatePlaylist />} />
            <Route path="liked" element={<LikedSongs />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#18181b',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.1)',
            },
          }}
        />
      </div>
    </Router>
  )
}

export default App
