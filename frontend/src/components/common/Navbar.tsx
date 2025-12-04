import { LogOut, User, ChevronLeft, ChevronRight, Bell } from 'lucide-react'
import { useStore } from '../../store/useStore'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'

import NotificationCenter from './NotificationCenter'
import UserMenu from './UserMenu'
import { useState } from 'react'

export default function Navbar() {
    const { user, logout, unreadCount } = useStore()
    const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
    const navigate = useNavigate()
    const location = useLocation()

    return (
        <motion.nav
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="h-20 px-8 flex items-center justify-between sticky top-0 z-20 bg-transparent"
        >
            <div className="flex items-center gap-6">
                <div className="flex gap-3">
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => {
                            if (window.location.pathname !== '/') {
                                navigate(-1)
                            }
                        }}
                        disabled={location.pathname === '/'}
                        className={`w-10 h-10 rounded-full bg-black/40 backdrop-blur-xl flex items-center justify-center text-white hover:bg-black/60 transition-colors border border-white/5 shadow-lg ${location.pathname === '/' ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        <ChevronLeft size={22} />
                    </motion.button>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => navigate(1)}
                        className="w-10 h-10 rounded-full bg-black/40 backdrop-blur-xl flex items-center justify-center text-white hover:bg-black/60 transition-colors disabled:opacity-50 border border-white/5 shadow-lg"
                    >
                        <ChevronRight size={22} />
                    </motion.button>
                </div>

                {/* Optional: Add search bar here if needed in future */}
            </div>

            <div className="flex items-center gap-5">


                <div className="h-8 w-px bg-white/10 mx-2" />

                <motion.button
                    whileHover={{ scale: 1.1, rotate: 15 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                    className="text-gray-400 hover:text-white p-2.5 rounded-full hover:bg-white/10 transition-colors relative"
                >
                    <Bell size={20} />
                    {unreadCount > 0 && (
                        <span className="absolute top-2 right-2.5 w-2 h-2 bg-primary rounded-full shadow-[0_0_8px_rgba(34,197,94,0.8)]" />
                    )}
                </motion.button>

                <NotificationCenter
                    isOpen={isNotificationsOpen}
                    onClose={() => setIsNotificationsOpen(false)}
                />

                <UserMenu />
            </div>
        </motion.nav>
    )
}
