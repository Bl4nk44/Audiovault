import type { StateCreator } from 'zustand'

export interface Notification {
    id: string
    type: 'success' | 'error' | 'info' | 'warning'
    message: string
    timestamp: number
    read: boolean
}

export interface NotificationSlice {
    notifications: Notification[]
    unreadCount: number
    addNotification: (type: Notification['type'], message: string) => void
    markAsRead: (id: string) => void
    markAllAsRead: () => void
    clearNotifications: () => void
    removeNotification: (id: string) => void
}

export const createNotificationSlice: StateCreator<NotificationSlice> = (set) => ({
    notifications: [],
    unreadCount: 0,
    addNotification: (type, message) => set((state) => {
        const newNotification: Notification = {
            id: Math.random().toString(36).substring(7),
            type,
            message,
            timestamp: Date.now(),
            read: false,
        }
        return {
            notifications: [newNotification, ...state.notifications],
            unreadCount: state.unreadCount + 1
        }
    }),
    markAsRead: (id) => set((state) => {
        const newNotifications = state.notifications.map(n =>
            n.id === id ? { ...n, read: true } : n
        )
        return {
            notifications: newNotifications,
            unreadCount: newNotifications.filter(n => !n.read).length
        }
    }),
    markAllAsRead: () => set((state) => ({
        notifications: state.notifications.map(n => ({ ...n, read: true })),
        unreadCount: 0
    })),
    clearNotifications: () => set({ notifications: [], unreadCount: 0 }),
    removeNotification: (id) => set((state) => {
        const newNotifications = state.notifications.filter(n => n.id !== id)
        return {
            notifications: newNotifications,
            unreadCount: newNotifications.filter(n => !n.read).length
        }
    })
})
