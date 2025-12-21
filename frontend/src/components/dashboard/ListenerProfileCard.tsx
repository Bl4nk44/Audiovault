import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { User } from 'lucide-react'
import api from '../../services/api'

interface Profile {
    top_artists: { name: string, count: number }[]
    vibe_description: string
}

export default function ListenerProfileCard() {
    const [profile, setProfile] = useState<Profile | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const response = await api.get('/history/profile')
                setProfile(response.data)
            } catch (error) {
                console.error("Failed to load profile", error)
            } finally {
                setLoading(false)
            }
        }
        fetchProfile()
    }, [])

    if (loading) return null
    if (!profile) return null

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="h-full rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6 relative overflow-hidden"
        >
            <div className="absolute top-0 right-0 w-32 h-32 bg-pink-500/10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />

            <div className="flex items-center gap-3 mb-6">
                <div className="p-2.5 rounded-xl bg-pink-500/20 text-pink-400 border border-pink-500/20">
                    <User size={20} />
                </div>
                <h3 className="font-bold text-xl text-white">Your Sonic Profile</h3>
            </div>

            <div className="space-y-6">
                <div>
                    <p className="text-sm text-gray-400 mb-2 uppercase tracking-wider font-semibold">Vibe Check</p>
                    <p className="text-lg text-white font-medium italic">"{profile.vibe_description}"</p>
                </div>

                <div>
                    <p className="text-sm text-gray-400 mb-3 uppercase tracking-wider font-semibold">Top Artists</p>
                    <div className="space-y-3">
                        {profile.top_artists.map((artist, i) => (
                            <div key={i} className="flex items-center justify-between group">
                                <div className="flex items-center gap-3">
                                    <span className="text-gray-500 font-mono text-sm w-4">0{i + 1}</span>
                                    <span className="text-white group-hover:text-pink-400 transition-colors">{artist.name}</span>
                                </div>
                                <div className="h-1 w-12 bg-white/10 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-pink-500/50"
                                        style={{ width: `${Math.min(artist.count * 10, 100)}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
