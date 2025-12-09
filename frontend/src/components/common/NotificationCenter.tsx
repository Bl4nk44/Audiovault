import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle, AlertCircle, Info, AlertTriangle, Trash2, Bell } from 'lucide-react'
import { useStore } from '../../store/useStore'
import { formatDistanceToNow } from 'date-fns'
import { pl, enUS } from 'date-fns/locale'
import { useTranslation } from '../../hooks/useTranslation'
import { useMemo } from 'react'

interface NotificationCenterProps {
    isOpen: boolean
    onClose: () => void
}

export default function NotificationCenter({ isOpen, onClose }: NotificationCenterProps) {
    const { notifications, markAllAsRead, clearNotifications, removeNotification, user } = useStore() // Added user
    const { t } = useTranslation()

    const locale = useMemo(() => {
        return user?.preferences?.language === 'pl' ? pl : enUS
    }, [user?.preferences?.language])

    const getIcon = (type: string) => {
        switch (type) {
            case 'success': return <CheckCircle size={18} className="text-green-500" />
            case 'error': return <AlertCircle size={18} className="text-red-500" />
            case 'warning': return <AlertTriangle size={18} className="text-orange-500" />
            default: return <Info size={18} className="text-blue-500" />
        }
    }

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-40 bg-transparent"
                    />
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute top-20 right-8 w-96 max-h-[600px] bg-[#18181b]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden"
                    >
                        <div className="p-4 border-b border-white/5 flex items-center justify-between bg-white/5">
                            <div className="flex items-center gap-2">
                                <Bell size={18} className="text-primary" />
                                <h3 className="font-bold text-white">{t('notifications.title')}</h3>
                                <span className="bg-white/10 text-xs px-2 py-0.5 rounded-full text-gray-400">
                                    {notifications.length}
                                </span>
                            </div>
                            <div className="flex items-center gap-1">
                                {notifications.length > 0 && (
                                    <>
                                        <button
                                            onClick={markAllAsRead}
                                            className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-white/10 transition-colors"
                                        >
                                            {t('notifications.markAllRead')}
                                        </button>
                                        <button
                                            onClick={clearNotifications}
                                            className="p-1.5 text-gray-400 hover:text-red-400 rounded hover:bg-white/10 transition-colors"
                                            title={t('notifications.clearAll')}
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>

                        <div className="overflow-y-auto custom-scrollbar flex-1 p-2 space-y-2">
                            {notifications.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                                    <Bell size={40} className="mb-3 opacity-20" />
                                    <p className="text-sm">{t('notifications.empty')}</p>
                                </div>
                            ) : (
                                notifications.map((notification) => (
                                    <motion.div
                                        key={notification.id}
                                        layout
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -20 }}
                                        className={`p-3 rounded-xl border border-white/5 relative group transition-colors ${notification.read ? 'bg-transparent opacity-70' : 'bg-white/5'}`}
                                    >
                                        <div className="flex gap-3">
                                            <div className="mt-0.5 flex-shrink-0">
                                                {getIcon(notification.type)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-gray-200 leading-snug break-words">
                                                    {notification.message}
                                                </p>
                                                <p className="text-xs text-gray-500 mt-1">
                                                    {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true, locale })}
                                                </p>
                                            </div>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                        removeNotification(notification.id)
                                                }}
                                                className="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-red-400 transition-all absolute top-2 right-2"
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                    </motion.div>
                                ))
                            )}
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    )
}
