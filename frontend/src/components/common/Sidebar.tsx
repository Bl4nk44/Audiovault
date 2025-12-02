import { Home, Search, Download, Library, PlusSquare, Heart } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/utils'
import { motion } from 'framer-motion'

const navItems = [
    { icon: Home, label: 'Home', path: '/' },
    { icon: Search, label: 'Search', path: '/search' },
    { icon: Library, label: 'Watchlist', path: '/watchlist' },
]

const libraryItems = [
    { icon: PlusSquare, label: 'Create Playlist', path: '/create-playlist', className: 'text-gray-400 group-hover:text-white' },
    { icon: Heart, label: 'Liked Songs', path: '/liked', className: 'text-purple-400 group-hover:text-purple-300' },
    { icon: Download, label: 'Downloads', path: '/queue', className: 'text-green-500 group-hover:text-green-400' },
]

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.05
        }
    }
}



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

                <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent my-2" />

                <div className="flex-1 flex flex-col overflow-hidden">
                    <div className="flex items-center justify-between mb-4 px-2">
                        <h2 className="text-gray-400 font-bold text-sm hover:text-white transition-colors cursor-pointer flex items-center gap-2 group uppercase tracking-wider">
                            <Library size={18} className="group-hover:text-primary transition-colors" />
                            Watchlist
                        </h2>
                        <motion.button
                            whileHover={{ scale: 1.1, rotate: 90 }}
                            whileTap={{ scale: 0.9 }}
                            className="text-gray-400 hover:text-white p-1.5 rounded-full hover:bg-white/10 transition-colors"
                        >
                            <PlusSquare size={20} />
                        </motion.button>
                    </div>

                    <div className="flex gap-2 mb-6 px-1 overflow-x-auto no-scrollbar">
                        <span className="bg-white/5 border border-white/5 px-4 py-1.5 rounded-full text-xs font-medium cursor-pointer hover:bg-white/10 hover:border-white/20 transition-all text-gray-300 hover:text-white whitespace-nowrap">Playlists</span>
                        <span className="bg-white/5 border border-white/5 px-4 py-1.5 rounded-full text-xs font-medium cursor-pointer hover:bg-white/10 hover:border-white/20 transition-all text-gray-300 hover:text-white whitespace-nowrap">Artists</span>
                    </div>

                    <motion.div
                        variants={container}
                        initial="hidden"
                        animate="show"
                        className="flex-1 overflow-y-auto pr-2 -mr-2 custom-scrollbar space-y-1"
                    >
                        {libraryItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) => cn(
                                    "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all group hover:bg-white/5 border border-transparent",
                                    isActive ? "bg-white/10 text-white border-white/5" : "text-gray-400"
                                )}
                            >
                                <div className={cn("w-8 h-8 flex items-center justify-center bg-gradient-to-br from-gray-800 to-black rounded-lg shadow-inner group-hover:shadow-lg transition-all", item.className && "bg-none shadow-none p-0")}>
                                    <item.icon size={18} className={cn("transition-transform group-hover:scale-110", item.className || "text-white")} />
                                </div>
                                <span className="group-hover:translate-x-1 transition-transform">{item.label}</span>
                            </NavLink>
                        ))}

                        {/* Playlists will be listed here */}
                    </motion.div>
                </div>
            </div>
        </motion.aside>
    )
}
