import { type StateCreator } from 'zustand'
import { type Download, type Track } from '../../types'

export interface QueueSlice {
    downloadQueue: Download[]
    addToQueue: (track: Track) => void
    removeFromQueue: (downloadId: string) => void
    updateProgress: (downloadId: string, progress: number) => void
}

export const createQueueSlice: StateCreator<QueueSlice> = (set) => ({
    downloadQueue: [],
    addToQueue: (track) => set((state) => ({
        downloadQueue: [...state.downloadQueue, {
            id: Math.random().toString(36).substr(2, 9), // Temp ID gen
            track,
            progress: 0,
            status: 'pending'
        }]
    })),
    removeFromQueue: (downloadId) => set((state) => ({
        downloadQueue: state.downloadQueue.filter(d => d.id !== downloadId)
    })),
    updateProgress: (downloadId, progress) => set((state) => ({
        downloadQueue: state.downloadQueue.map(d =>
            d.id === downloadId ? { ...d, progress } : d
        )
    }))
})
