import { Bell } from 'lucide-react'
import { useStore } from '../../store/useStore'
import { motion } from 'framer-motion'

import NotificationCenter from './NotificationCenter'
import UserMenu from './UserMenu'
import { useState } from 'react'

export default function Navbar() {
    const { unreadCount } = useStore()
    const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)

    return (
        <motion.nav
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="h-20 px-8 flex items-center justify-between sticky top-0 z-20 bg-transparent"
        >
            <div className="flex items-center gap-6">
                {/* Navigation arrows removed */}

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
