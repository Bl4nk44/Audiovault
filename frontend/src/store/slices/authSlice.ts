import { type StateCreator } from 'zustand'
import { type User } from '../../types'

export interface AuthSlice {
    user: User | null
    isAuthenticated: boolean
    token: string | null
    sessions: Record<string, { user: User; token: string }>
    setUser: (user: User | null) => void
    setToken: (token: string | null) => void
    addSession: (user: User, token: string) => void
    switchSession: (userId: string) => void
    removeSession: (userId: string) => void
    updateUserPreferences: (prefs: Record<string, any>) => void
    logout: () => void
}

export const createAuthSlice: StateCreator<AuthSlice> = (set, get) => ({
    user: null,
    isAuthenticated: !!localStorage.getItem('access_token'),
    token: localStorage.getItem('access_token'),
    sessions: JSON.parse(localStorage.getItem('sessions') || '{}'),

    setUser: (user) => set({ user }),

    setToken: (token) => {
        if (token) {
            localStorage.setItem('access_token', token)
        } else {
            localStorage.removeItem('access_token')
        }
        set({ token, isAuthenticated: !!token })
    },

    addSession: (user, token) => {
        const sessions = { ...get().sessions, [user.id]: { user, token } }
        localStorage.setItem('sessions', JSON.stringify(sessions))

        // Also set as current
        localStorage.setItem('access_token', token)
        set({ sessions, user, token, isAuthenticated: true })
    },

    switchSession: (userId) => {
        const session = get().sessions[userId]
        if (session) {
            localStorage.setItem('access_token', session.token)
            set({ user: session.user, token: session.token, isAuthenticated: true })
            window.location.reload() // Reload to refresh state/sockets
        }
    },

    removeSession: (userId) => {
        const sessions = { ...get().sessions }
        delete sessions[userId]
        localStorage.setItem('sessions', JSON.stringify(sessions))
        set({ sessions })

        // If removing current session, logout
        if (get().user?.id === userId) {
            get().logout()
        }
    },

    updateUserPreferences: (prefs: Record<string, any>) => {
        const user = get().user
        if (user) {
            const updatedUser = { ...user, preferences: { ...user.preferences, ...prefs } }
            set({ user: updatedUser })

            // Also update session in localStorage
            const sessions = { ...get().sessions }
            if (sessions[user.id]) {
                sessions[user.id].user = updatedUser
                localStorage.setItem('sessions', JSON.stringify(sessions))
            }
        }
    },

    logout: () => {
        localStorage.removeItem('access_token')
        set({ user: null, token: null, isAuthenticated: false })
    }
})
