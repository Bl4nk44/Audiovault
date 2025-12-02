import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Play, Sparkles } from 'lucide-react'
import api from '../../services/api'
import { useStore } from '../../store/useStore'
import toast from 'react-hot-toast'

interface Recommendation {
    id: string
    title: string
    description: string
    tracks: any[]
}

export default function WeeklyMix() {
    const [mix, setMix] = useState<Recommendation | null>(null)
    const [loading, setLoading] = useState(true)
    const { playTrack } = useStore()

    useEffect(() => {
        fetchWeeklyMix()
    }, [])

    const fetchWeeklyMix = async () => {
        try {
            // Try to get existing first
            const response = await api.get('/history/recommendations')
            const weekly = response.data.find((r: any) => r.type === 'weekly')

            if (weekly) {
                setMix(weekly)
            } else {
                // Generate new if not exists
                const genResponse = await api.post('/history/generate-weekly')
                if (genResponse.data) {
                    setMix(genResponse.data)
                }
            }
        } catch (error) {
            console.error("Failed to load weekly mix", error)
        } finally {
            setLoading(false)
        }
    }

    const handlePlay = () => {
        if (mix && mix.tracks.length > 0) {
            playTrack(mix.tracks[0])
            toast.success(`Playing ${mix.title}`)
        }
    }

    if (loading) return null // Skeleton could be better
    if (!mix) return null

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-purple-900/50 to-blue-900/50 border border-white/10 p-6 group cursor-pointer"
            onClick={handlePlay}
        >
            {/* Background Glow */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/20 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 group-hover:bg-primary/30 transition-colors" />

            <div className="relative z-10 flex items-center gap-6">
                <div className="w-32 h-32 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 shadow-lg flex items-center justify-center group-hover:scale-105 transition-transform duration-300">
                    <Sparkles className="text-white w-12 h-12" />
                </div>

                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                        <span className="px-3 py-1 rounded-full bg-white/10 text-xs font-medium text-white backdrop-blur-sm border border-white/10">
                            AI Curated
                        </span>
                        <span className="text-xs text-gray-400">Updated Weekly</span>
                    </div>

                    <h2 className="text-3xl font-bold text-white mb-2">{mix.title}</h2>
                    <p className="text-gray-300 line-clamp-2">{mix.description}</p>

                    <div className="mt-4 flex items-center gap-4">
                        <button className="w-12 h-12 rounded-full bg-primary text-black flex items-center justify-center hover:scale-110 transition-transform shadow-[0_0_20px_rgba(34,197,94,0.4)]">
                            <Play fill="currentColor" className="ml-1" />
                        </button>
                        <span className="text-sm text-gray-400 font-medium">{mix.tracks.length} tracks</span>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
