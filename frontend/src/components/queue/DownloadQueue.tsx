import { useEffect, useState } from 'react'
import api from '../../services/api'
import DownloadItem from './DownloadItem'
import { Loader2, Music2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function DownloadQueue() {
    const [queue, setQueue] = useState<any[]>([])
    const [isLoading, setIsLoading] = useState(true)

    const fetchQueue = async () => {
        try {
            const response = await api.get('/downloads/queue')
            setQueue(response.data)
        } catch (error) {
            console.error('Failed to fetch queue', error)
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchQueue()
        const interval = setInterval(fetchQueue, 2000)

        const handleProgress = (e: any) => {
            setQueue(prev => prev.map(item =>
                item.id === e.detail.download_id
                    ? { ...item, progress: e.detail.progress, status: 'downloading' }
                    : item
            ))
        }

        const handleCompleted = () => {
            fetchQueue()
        }

        window.addEventListener('download:progress', handleProgress as any)
        window.addEventListener('download:completed', handleCompleted as any)

        return () => {
            clearInterval(interval)
            window.removeEventListener('download:progress', handleProgress as any)
            window.removeEventListener('download:completed', handleCompleted as any)
        }
    }, [])

    if (isLoading) {
        return (
            <div className="flex justify-center p-12">
                <Loader2 className="animate-spin text-primary" size={40} />
            </div>
        )
    }

    if (queue.length === 0) {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center justify-center py-20 px-4 rounded-3xl bg-white/5 border border-white/10 backdrop-blur-md text-center"
            >
                <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-6 shadow-inner">
                    <Music2 size={40} className="text-gray-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Queue is empty</h3>
                <p className="text-gray-400 max-w-sm">
                    Start downloading tracks to see them appear here.
                </p>
            </motion.div>
        )
    }

    return (
        <div className="space-y-4 pb-20">
            <AnimatePresence mode='popLayout'>
                {queue.map((item) => (
                    <DownloadItem key={item.id} item={item} />
                ))}
            </AnimatePresence>
        </div>
    )
}
