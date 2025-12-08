import { Home, Search, Settings as SettingsIcon, Eye, Music, Download } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/utils'
import { motion } from 'framer-motion'

const navItems = [
    { icon: Home, label: 'Home', path: '/' },
    { icon: Search, label: 'Search', path: '/search' },
    { icon: Eye, label: 'Watchlist', path: '/watchlist' },
    { icon: Music, label: 'My Library', path: '/library' },
    { icon: Download, label: 'Downloads', path: '/queue' },
    { icon: SettingsIcon, label: 'Settings', path: '/settings' },
]



export default function Sidebar() {
    return (
        <motion.aside
            initial={{ x: -100, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="w-full h-full flex flex-col gap-4 z-30"
        >
            <div className="bg-black/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-6 flex flex-col gap-6 shadow-2xl h-full">
                <motion.h1
                    whileHover={{ scale: 1.02 }}
                    className="text-2xl font-bold flex items-center gap-3 text-white cursor-default px-2"
                >
                    <div className="relative">
                        <div className="absolute inset-0 bg-primary/50 blur-lg rounded-full" />
                        <span className="relative w-10 h-10 bg-gradient-to-br from-primary to-green-600 rounded-xl flex items-center justify-center text-black shadow-lg">
                            S
                        </span>
                    </div>
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 tracking-tight">Spotizerr</span>
                </motion.h1>

                <nav className="flex flex-col gap-2">
                    {navItems.map((navItem) => (
                        <NavLink
                            key={navItem.path}
                            to={navItem.path}
                            className={({ isActive }) => cn(
                                "flex items-center gap-4 text-base font-bold transition-all duration-300 px-4 py-3.5 rounded-xl group relative overflow-hidden",
                                isActive
                                    ? "text-white bg-white/10 shadow-[0_0_15px_rgba(255,255,255,0.05)] border border-white/5"
                                    : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
                            )}
                        >
                            {({ isActive }) => (
                                <>
                                    {isActive && (
                                        <motion.div
                                            layoutId="activeNav"
                                            className="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-primary rounded-r-full shadow-[0_0_10px_rgba(34,197,94,0.8)]"
                                        />
                                    )}
                                    <navItem.icon size={24} className={cn("transition-transform duration-300 group-hover:scale-110", isActive && "text-primary drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]")} />
                                    <span className="relative z-10">{navItem.label}</span>
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                {/* Watchlist section removed */}
            </div>
        </motion.aside >
    )
}
