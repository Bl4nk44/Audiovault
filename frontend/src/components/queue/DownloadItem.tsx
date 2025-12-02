import { Download, AlertCircle, CheckCircle, Loader2, Music } from 'lucide-react'

import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

import { useStore } from '../../store/useStore'

interface DownloadItemProps {
    item: {
        id: string
        track_id?: string
        track: {
            title: string
            artist: string
            image_url?: string
        }
        status: string
        progress: number
        error_message?: string
    }
}

export default function DownloadItem({ item }: DownloadItemProps) {
    const { playTrack } = useStore()

    const handlePlay = () => {
        if (item.status === 'completed') {
            playTrack({
                id: item.track_id || item.id,
                title: item.track.title,
                artist: item.track.artist,
                cover: item.track.image_url,
                source: 'download'
            })
        }
    }

    const getStatusIcon = () => {
        switch (item.status) {
            case 'completed':
                return <CheckCircle className="text-green-500 drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]" size={24} />
            case 'failed':
                return <AlertCircle className="text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" size={24} />
            case 'downloading':
            case 'processing':
                return <Loader2 className="animate-spin text-primary drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]" size={24} />
            default:
                return <Download className="text-gray-400" size={24} />
        }
    }

    return (
        <motion.div
            layout
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
            onClick={handlePlay}
            className={cn(
                "group relative bg-white/5 backdrop-blur-md border border-white/5 rounded-2xl p-4 flex items-center gap-5 transition-all shadow-lg",
                item.status === 'completed' ? "cursor-pointer hover:bg-white/10 hover:scale-[1.02]" : ""
            )}
        >
            {/* Cover Image */}
            <div className="w-16 h-16 bg-black/40 rounded-xl overflow-hidden flex-shrink-0 border border-white/10 shadow-md relative group-hover:scale-105 transition-transform duration-300">
                {item.track.image_url ? (
                    <img src={item.track.image_url} alt={item.track.title} className="w-full h-full object-cover" />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-500">
                        <Music size={24} />
                    </div>
                )}

                {/* Progress Overlay for Image */}
                {item.status === 'downloading' && (
                    <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                        <span className="text-xs font-bold text-primary">{Math.round(item.progress)}%</span>
                    </div>
                )}
            </div>

            <div className="flex-1 min-w-0 space-y-1">
                <div className="flex justify-between items-start">
                    <div>
                        <h4 className="font-bold text-white truncate text-lg leading-tight">{item.track.title}</h4>
                        <p className="text-sm text-gray-400 truncate">{item.track.artist}</p>
                    </div>
                </div>

                {/* Progress Bar */}
                {item.status === 'downloading' && (
                    <div className="relative h-1.5 w-full bg-white/10 rounded-full overflow-hidden mt-2">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${item.progress}%` }}
                            transition={{ ease: "linear" }}
                            className="absolute top-0 left-0 h-full bg-primary shadow-[0_0_10px_rgba(34,197,94,0.5)]"
                        />
                    </div>
                )}

                {/* Error Message */}
                {item.status === 'failed' && (
                    <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                        {item.error_message}
                    </p>
                )}

                {/* Status Text */}
                {item.status === 'processing' && (
                    <p className="text-xs text-primary mt-1 animate-pulse">Processing metadata...</p>
                )}
            </div>

            <div className="flex-shrink-0 pl-4">
                {getStatusIcon()}
            </div>
        </motion.div>
    )
}
