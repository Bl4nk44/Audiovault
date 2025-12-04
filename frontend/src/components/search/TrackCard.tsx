import { Play, Download, Plus, MoreHorizontal, Music } from 'lucide-react'
import api from '../../services/api'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'

import { useStore } from '../../store/useStore'

interface Track {
    id: string
    title: string
    artist: string
    album: string
    image_url: string | null
    source: 'spotify' | 'youtube' | 'deezer'
    duration_ms: number
}

interface TrackCardProps {
    track: Track
}

export default function TrackCard({ track }: TrackCardProps) {
    const { playTrack } = useStore()

    const handlePlay = () => {
        playTrack({
            id: track.id,
            title: track.title,
            artist: track.artist,
            cover: track.image_url || undefined,
            source: track.source,
            duration: track.duration_ms / 1000
        })
    }

    const handleDownload = async (e: React.MouseEvent) => {
        e.stopPropagation()
        try {
            await api.post('/downloads/add', {
                track_id: track.id,
                source: track.source
            })
            toast.success('Added to download queue')
        } catch (error) {
            toast.error('Failed to add to queue')
        }
    }

    const handleAddToWatchlist = async (e: React.MouseEvent) => {
        e.stopPropagation()
        try {
            await api.post('/watchlist/add', {
                watch_type: 'track',
                source: track.source,
                source_id: track.id,
                source_name: track.title,
                auto_download: false
            })
            toast.success('Added to library')
        } catch (error) {
            toast.error('Failed to add to library')
        }
    }

    const formatDuration = (ms: number) => {
        const minutes = Math.floor(ms / 60000)
        const seconds = ((ms % 60000) / 1000).toFixed(0)
        return `${minutes}:${Number(seconds) < 10 ? '0' : ''}${seconds}`
    }

    return (
        <motion.div
            whileHover={{ scale: 1.02, backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
            onClick={handlePlay}
            className="group relative flex items-center gap-4 p-3 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-all cursor-pointer overflow-hidden"
        >
            <div className="relative w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 shadow-lg group-hover:shadow-primary/20 transition-all">
                {track.image_url ? (
                    <img src={track.image_url} alt={track.title} className="w-full h-full object-cover" />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                        <Music className="text-gray-600" />
                    </div>
                )}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <Play className="text-white fill-white" size={24} />
                </div>
            </div>

            <div className="flex-1 min-w-0">
                <h3 className="font-bold text-white truncate group-hover:text-primary transition-colors">{track.title}</h3>
                <p className="text-sm text-gray-400 truncate">{track.artist}</p>
            </div>

            <div className="flex items-center gap-4 mr-2">
                <span className="text-xs text-gray-500 font-medium hidden sm:block">{formatDuration(track.duration_ms)}</span>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity translate-x-4 group-hover:translate-x-0">
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={handleAddToWatchlist}
                        className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                        title="Add to Library"
                    >
                        <Plus size={18} />
                    </motion.button>

                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={handleDownload}
                        className="p-2 text-gray-400 hover:text-primary hover:bg-primary/10 rounded-full transition-colors"
                        title="Download"
                    >
                        <Download size={18} />
                    </motion.button>

                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                    >
                        <MoreHorizontal size={18} />
                    </motion.button>
                </div>
            </div>
        </motion.div>
    )
}
