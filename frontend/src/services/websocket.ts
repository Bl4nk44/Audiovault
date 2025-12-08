import { io, Socket } from 'socket.io-client'
import { useStore } from '../store/useStore'
import toast from 'react-hot-toast'

let socket: Socket | null = null

export const initializeWebSocket = () => {
    const token = useStore.getState().token
    if (!token) return

    socket = io(import.meta.env.VITE_WS_URL || 'http://localhost:8000', {
        auth: {
            token: token,
        },
        transports: ['websocket'],
    })

    socket.on('connect', () => {

    })

    socket.on('download:progress', (data) => {
        // Dispatch to store if we had a slice for it, or just emit event
        // For now, we might handle this in the component or store
        // Let's assume we dispatch a custom event or use store
        window.dispatchEvent(new CustomEvent('download:progress', { detail: data }))
    })

    socket.on('download:completed', (data) => {
        toast.success(`Download completed: ${data.filename}`)
        window.dispatchEvent(new CustomEvent('download:completed', { detail: data }))
    })

    socket.on('download:error', (data) => {
        toast.error(`Download failed: ${data.error}`)
        window.dispatchEvent(new CustomEvent('download:error', { detail: data }))
    })

    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket')
    })
}

export const disconnectWebSocket = () => {
    if (socket) {
        socket.disconnect()
        socket = null
    }
}
