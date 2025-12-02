import { Download, Music, Clock, HardDrive, Play } from 'lucide-react'
import { motion } from 'framer-motion'
import Button from '../components/ui/Button'
import ProgressBar from '../components/ui/ProgressBar'
import WeeklyMix from '../components/dashboard/WeeklyMix'
import DiscoveryPlaylist from '../components/dashboard/DiscoveryPlaylist'
import ListenerProfileCard from '../components/dashboard/ListenerProfileCard'
import { useEffect, useState } from 'react'
import api from '../services/api'

interface DashboardStats {
    total_downloads: string
    tracks_in_library: string
    pending_queue: string
    storage_free: string
}

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.1
        }
    }
}

const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
}

import { useNavigate } from 'react-router-dom'

export default function Dashboard() {
    const navigate = useNavigate()
    const [dashboardStats, setDashboardStats] = useState<DashboardStats>({
        total_downloads: '-',
        tracks_in_library: '-',
        pending_queue: '-',
        storage_free: '-'
    })

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const response = await api.get('/dashboard/stats')
                setDashboardStats(response.data)
            } catch (error) {
                console.error('Failed to fetch dashboard stats', error)
            }
        }
        fetchStats()
    }, [])

    const stats = [
        { label: 'Total Downloads', value: dashboardStats.total_downloads, icon: Download, color: 'text-blue-400', gradient: 'from-blue-500/20 to-blue-600/5' },
        { label: 'Tracks in Library', value: dashboardStats.tracks_in_library, icon: Music, color: 'text-green-400', gradient: 'from-green-500/20 to-green-600/5' },
        { label: 'Pending Queue', value: dashboardStats.pending_queue, icon: Clock, color: 'text-orange-400', gradient: 'from-orange-500/20 to-orange-600/5' },
        { label: 'Storage Free', value: dashboardStats.storage_free, icon: HardDrive, color: 'text-purple-400', gradient: 'from-purple-500/20 to-purple-600/5' },
    ]

    return (
        <div className="relative min-h-screen">
            {/* Ambient Background */}
            <div className="fixed top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
                <div className="absolute top-[10%] right-[10%] w-[40%] h-[40%] bg-purple-500/5 rounded-full blur-[150px] animate-blob" />
                <div className="absolute bottom-[10%] left-[20%] w-[30%] h-[30%] bg-blue-500/5 rounded-full blur-[150px] animate-blob animation-delay-2000" />
            </div>

            <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="relative z-10 space-y-8 p-6"
            >
                <motion.div variants={item}>
                    <h2 className="text-4xl font-bold tracking-tight text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">Dashboard</h2>
                    <p className="text-gray-400 mt-2 text-lg">Overview of your music collection and downloads.</p>
                </motion.div>

                <motion.div
                    variants={container}
                    className="grid gap-6 md:grid-cols-2 lg:grid-cols-4"
                >
                    {stats.map((stat) => (
                        <motion.div
                            key={stat.label}
                            variants={item}
                            whileHover={{ scale: 1.02, y: -5 }}
                            className={`p-6 rounded-3xl border border-white/10 bg-gradient-to-br ${stat.gradient} backdrop-blur-xl shadow-xl relative overflow-hidden group`}
                        >
                            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500">
                                <stat.icon size={100} />
                            </div>

                            <div className="flex items-center justify-between space-y-0 pb-4 relative z-10">
                                <p className="text-sm font-medium text-gray-300">{stat.label}</p>

                            </div>
                            <div className="text-4xl font-bold text-white relative z-10 drop-shadow-md">{stat.value}</div>
                        </motion.div>
                    ))}
                </motion.div>

                <div className="grid gap-6 md:grid-cols-2">
                    <motion.div variants={item}>
                        <WeeklyMix />
                    </motion.div>
                    <motion.div variants={item}>
                        <DiscoveryPlaylist />
                    </motion.div>
                </div>

                <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-7">
                    <motion.div
                        variants={item}
                        className="col-span-4 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8 shadow-2xl space-y-8"
                    >
                        <ListenerProfileCard />

                        <div>
                            <h3 className="font-bold mb-8 text-2xl text-white flex items-center gap-3">
                                <span className="w-1.5 h-8 bg-primary rounded-full shadow-[0_0_10px_rgba(34,197,94,0.5)]"></span>
                                Recent Activity
                            </h3>
                            <div className="space-y-4">
                                {[1, 2, 3].map((i) => (
                                    <motion.div
                                        key={i}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.1 }}
                                        className="flex items-center gap-4 p-4 rounded-2xl hover:bg-white/5 transition-colors group cursor-pointer border border-transparent hover:border-white/10"
                                    >
                                        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-gray-800 to-black flex items-center justify-center shadow-lg group-hover:shadow-primary/20 transition-all relative overflow-hidden">
                                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity backdrop-blur-[1px]">
                                                <Play size={24} className="text-white fill-white" />
                                            </div>
                                            <Music size={24} className="text-gray-500 group-hover:opacity-0 transition-opacity" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-bold text-white group-hover:text-primary transition-colors truncate">Blinding Lights</p>
                                            <p className="text-sm text-gray-400 truncate">The Weeknd • Downloaded 2h ago</p>
                                        </div>
                                        <div className="w-32 hidden sm:block">
                                            <ProgressBar progress={75} height="h-1.5" showLabel={false} />
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </motion.div>

                    <motion.div
                        variants={item}
                        className="col-span-3 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-8 shadow-2xl flex flex-col"
                    >
                        <h3 className="font-bold mb-8 text-2xl text-white flex items-center gap-3">
                            <span className="w-1.5 h-8 bg-purple-500 rounded-full shadow-[0_0_10px_rgba(168,85,247,0.5)]"></span>
                            Quick Actions
                        </h3>
                        <div className="space-y-4 flex-1">
                            <Button
                                variant="primary"
                                className="w-full justify-start h-14 text-lg font-bold shadow-lg shadow-primary/20"
                                size="lg"
                                onClick={() => navigate('/search')}
                            >
                                <Download className="mr-3 h-6 w-6" /> Add New Download
                            </Button>
                            <Button
                                variant="secondary"
                                className="w-full justify-start h-14 text-lg bg-white/5 hover:bg-white/10 border border-white/10"
                                size="lg"
                                onClick={() => navigate('/search')}
                            >
                                <Music className="mr-3 h-6 w-6" /> Import Playlist
                            </Button>
                            <Button
                                variant="outline"
                                className="w-full justify-start h-14 text-lg border-white/10 hover:bg-white/5 text-gray-300 hover:text-white"
                                size="lg"
                                onClick={() => navigate('/watchlist')}
                            >
                                <Clock className="mr-3 h-6 w-6" /> View Watchlist
                            </Button>
                        </div>

                        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary/10 to-transparent border border-primary/20 relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                            <div className="flex items-center gap-3 mb-4 relative z-10">
                                <div className="p-2.5 rounded-xl bg-primary/20 text-primary border border-primary/20 shadow-[0_0_15px_rgba(34,197,94,0.3)]">
                                    <Download size={20} />
                                </div>
                                <span className="font-bold text-white">Downloading...</span>
                            </div>
                            <p className="text-sm text-gray-300 mb-3 relative z-10">Downloading "Starboy" - 45%</p>
                            <div className="relative z-10">
                                <ProgressBar progress={45} showLabel height="h-2" />
                            </div>
                        </div>
                    </motion.div>
                </div>
            </motion.div>
        </div>
    )
}
