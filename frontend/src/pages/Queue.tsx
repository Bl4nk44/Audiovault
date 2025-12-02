import DownloadQueue from '../components/queue/DownloadQueue'
import { motion } from 'framer-motion'

export default function Queue() {
    return (
        <div className="relative min-h-screen">
            {/* Ambient Background */}
            <div className="fixed top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
                <div className="absolute top-[20%] right-[10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] animate-pulse" />
                <div className="absolute bottom-[10%] left-[20%] w-[30%] h-[30%] bg-purple-500/10 rounded-full blur-[100px] animate-pulse delay-1000" />
            </div>

            <div className="relative z-10 space-y-8 p-6">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col gap-2"
                >
                    <h1 className="text-4xl font-bold tracking-tight text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">
                        Download Queue
                    </h1>
                    <p className="text-gray-400 text-lg">
                        Manage your active downloads and history.
                    </p>
                </motion.div>

                <DownloadQueue />
            </div>
        </div>
    )
}
