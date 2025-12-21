import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { User, LogOut, Settings, ChevronDown, Plus } from 'lucide-react'
import { useStore } from '../../store/useStore'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from '../../hooks/useTranslation'

export default function UserMenu() {
    const { user, logout, sessions, switchSession, removeSession } = useStore()
    const [isOpen, setIsOpen] = useState(false)
    const navigate = useNavigate()
    const menuRef = useRef<HTMLDivElement>(null)
    const { t } = useTranslation()

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    const getAvatarSrc = (url?: string) => {
        if (!url) return undefined
        if (url.startsWith('http')) return url
        return `${import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://localhost:8000'}${url}`
    }

    const otherSessions = Object.values(sessions).filter(s => s.user.id !== user?.id)

    return (
        <div className="relative" ref={menuRef}>
            <motion.button
                whileHover={{ scale: 1.02 }}
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 bg-black/40 backdrop-blur-xl border border-white/5 p-1.5 pr-4 rounded-full hover:bg-black/60 transition-colors cursor-pointer group shadow-lg"
            >
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-green-600 flex items-center justify-center shadow-lg group-hover:shadow-primary/30 transition-shadow overflow-hidden">
                    {user?.preferences?.avatar_url ? (
                        <img src={getAvatarSrc(user.preferences.avatar_url)} alt="Avatar" className="w-full h-full object-cover" />
                    ) : (
                        <User size={18} className="text-black" />
                    )}
                </div>
                <span className="text-sm font-bold text-white group-hover:text-primary transition-colors max-w-[100px] truncate">
                    {user?.username || 'User'}
                </span>
                <ChevronDown size={16} className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </motion.button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute top-14 right-0 w-64 bg-[#18181b]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden"
                    >
                        <div className="p-4 border-b border-white/5">
                            <p className="text-xs text-gray-400 uppercase font-bold tracking-wider mb-2">{t('usermenu.currentAccount')}</p>
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-green-600 flex items-center justify-center shadow-lg overflow-hidden">
                                    {user?.preferences?.avatar_url ? (
                                        <img src={getAvatarSrc(user.preferences.avatar_url)} alt="Avatar" className="w-full h-full object-cover" />
                                    ) : (
                                        <User size={20} className="text-black" />
                                    )}
                                </div>
                                <div className="overflow-hidden">
                                    <p className="font-bold text-white truncate">{user?.username}</p>
                                    <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                                </div>
                            </div>
                        </div>

                        {otherSessions.length > 0 && (
                            <div className="p-2 border-b border-white/5 bg-white/5">
                                <p className="text-xs text-gray-400 uppercase font-bold tracking-wider px-2 mb-2 mt-1">{t('usermenu.switchAccount')}</p>
                                {otherSessions.map((session) => (
                                    <div key={session.user.id} className="flex items-center justify-between p-2 rounded-xl hover:bg-white/10 transition-colors group">
                                        <button
                                            onClick={() => switchSession(session.user.id)}
                                            className="flex items-center gap-3 flex-1 min-w-0 text-left"
                                        >
                                            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                                                <User size={14} className="text-gray-300" />
                                            </div>
                                            <span className="text-sm font-medium text-gray-200 truncate">{session.user.username}</span>
                                        </button>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                removeSession(session.user.id)
                                            }}
                                            className="p-1.5 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                                            title="Remove account"
                                        >
                                            <LogOut size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="p-2 space-y-1">
                            <button
                                onClick={() => {
                                    logout()
                                    navigate('/login')
                                }}
                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
                            >
                                <Plus size={18} />
                                {t('usermenu.addAccount')}
                            </button>
                            <button
                                onClick={() => {
                                    setIsOpen(false)
                                    navigate('/settings')
                                }}
                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
                            >
                                <Settings size={18} />
                                {t('usermenu.settings')}
                            </button>
                            <div className="h-px bg-white/10 my-1" />
                            <button
                                onClick={handleLogout}
                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                            >
                                <LogOut size={18} />
                                {t('usermenu.logout')}
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
