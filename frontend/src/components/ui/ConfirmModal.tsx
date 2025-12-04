import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, X } from 'lucide-react'
import Button from './Button'
import { createPortal } from 'react-dom'

interface ConfirmModalProps {
    isOpen: boolean
    onClose: () => void
    onConfirm: () => void
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    variant?: 'danger' | 'info'
}

export default function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    variant = 'danger'
}: ConfirmModalProps) {
    if (!isOpen) return null

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
                    />

                    {/* Modal */}
                    <div className="fixed inset-0 flex items-center justify-center z-[101] pointer-events-none">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 20 }}
                            className="w-full max-w-md mx-4 pointer-events-auto"
                        >
                            <div className="bg-[#1a1a1a] border border-white/10 rounded-2xl shadow-2xl overflow-hidden relative">
                                {/* Header Gradient Line */}
                                <div className={`h-1 w-full bg-gradient-to-r ${variant === 'danger' ? 'from-red-500 to-orange-500' : 'from-blue-500 to-purple-500'}`} />

                                <div className="p-6">
                                    <div className="flex items-start gap-4">
                                        <div className={`p-3 rounded-full ${variant === 'danger' ? 'bg-red-500/10 text-red-500' : 'bg-blue-500/10 text-blue-500'}`}>
                                            <AlertTriangle size={24} />
                                        </div>
                                        <div className="flex-1">
                                            <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
                                            <p className="text-gray-400 leading-relaxed">{message}</p>
                                        </div>
                                        <button
                                            onClick={onClose}
                                            className="text-gray-500 hover:text-white transition-colors"
                                        >
                                            <X size={20} />
                                        </button>
                                    </div>

                                    <div className="flex justify-end gap-3 mt-8">
                                        <Button
                                            variant="secondary"
                                            onClick={onClose}
                                            className="bg-white/5 hover:bg-white/10 text-white border-white/5"
                                        >
                                            {cancelText}
                                        </Button>
                                        <Button
                                            variant={variant === 'danger' ? 'primary' : 'primary'} // Button component might not have danger variant, using primary or custom styling
                                            onClick={() => {
                                                onConfirm()
                                                onClose()
                                            }}
                                            className={variant === 'danger' ? '!bg-red-500 hover:!bg-red-600 text-white shadow-lg shadow-red-500/20' : ''}
                                        >
                                            {confirmText}
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                </>
            )}
        </AnimatePresence>,
        document.body
    )
}
