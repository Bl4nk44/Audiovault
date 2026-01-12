import { type StateCreator } from 'zustand'
import { type Download, type Track } from '../../types'
import { downloadsApi } from '../../api/downloads'


export interface QueueSlice {
    downloadQueue: Download[]
    addToQueue: (track: Track) => void
    removeFromQueue: (downloadId: string) => void
    updateProgress: (downloadId: string, progress: number) => void
    updateStatus: (downloadId: string, status: Download['status'], error?: string) => void
    pauseDownload: (downloadId: string) => Promise<void>
    resumeDownload: (downloadId: string) => Promise<void>
    retryDownload: (downloadId: string) => Promise<void>
    fetchDownloads: () => Promise<void>
}

export const createQueueSlice: StateCreator<QueueSlice> = (set) => ({
    downloadQueue: [],
    addToQueue: (track) => set((state: QueueSlice) => ({
        downloadQueue: [...state.downloadQueue, {
            id: Math.random().toString(36).slice(2, 11), // Temp ID gen
            track,
            progress: 0,
            status: 'pending'
        }]
    })),
    removeFromQueue: (downloadId) => set((state: QueueSlice) => ({
        downloadQueue: state.downloadQueue.filter((d: Download) => d.id !== downloadId)
    })),
    updateProgress: (downloadId, progress) => set((state: QueueSlice) => ({
        downloadQueue: state.downloadQueue.map((d: Download) =>
            d.id === downloadId ? { ...d, progress } : d
        )
    })),
    updateStatus: (downloadId, status, error) => set((state: QueueSlice) => ({
        downloadQueue: state.downloadQueue.map((d: Download) =>
            d.id === downloadId ? { ...d, status, error } : d
        )
    })),
    pauseDownload: async (downloadId: string) => {
        // Optimistic update
        set((state: QueueSlice) => ({
            downloadQueue: state.downloadQueue.map((d: Download) =>
                d.id === downloadId ? { ...d, status: 'paused' as const } : d
            )
        }));
        try {
            await downloadsApi.pause(downloadId);
        } catch (error) {
            console.error("Failed to pause", error);
            // Revert on error? Or just let polling/websocket sync it eventually.
        }
    },
    resumeDownload: async (downloadId: string) => {
        set((state: QueueSlice) => ({
            downloadQueue: state.downloadQueue.map((d: Download) =>
                d.id === downloadId ? { ...d, status: 'pending' as const } : d
            )
        }));
        try {
            await downloadsApi.resume(downloadId);
        } catch (error) {
            console.error("Failed to resume", error);
        }
    },

    retryDownload: async (downloadId: string) => {
        set((state: QueueSlice) => ({
            downloadQueue: state.downloadQueue.map((d: Download) =>
                d.id === downloadId ? { ...d, status: 'pending' as const, error: undefined } : d
            )
        }));
        try {
            await downloadsApi.retry(downloadId);
        } catch (error) {
            console.error("Failed to retry", error);
        }
    },
    fetchDownloads: async () => {
        try {
            const downloads = await downloadsApi.getAll();
            set({ downloadQueue: downloads });
        } catch (error) {
            console.error("Failed to fetch downloads", error);
        }
    }
})
