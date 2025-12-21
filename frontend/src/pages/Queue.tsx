import DownloadQueue from '../components/queue/DownloadQueue'
import { motion } from 'framer-motion'

export default function Queue() {
    return (
        <div className="relative min-h-screen">


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
