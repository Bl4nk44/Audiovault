import WatchlistManager from '../components/watchlist/WatchlistManager'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ConfirmModal from '../components/ui/ConfirmModal'
import toast from 'react-hot-toast'
import api from '../services/api'

export default function Watchlist() {
    const navigate = useNavigate()
    const [showRescanModal, setShowRescanModal] = useState(false)

    const handleRescan = async () => {
        try {
            const res = await api.post('/downloads/rescan')
            toast.success(`Rescan complete. Found ${res.data.rescanned_count} missing files.`)
            setShowRescanModal(false)
        } catch (e) {
            console.error("Rescan failed", e)
            toast.error("Rescan failed")
            setShowRescanModal(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
                    <p className="text-muted-foreground">Track new releases from your favorite artists and channels.</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => setShowRescanModal(true)}
                        className="bg-white/10 text-white px-4 py-2 rounded-lg hover:bg-white/20 transition-colors border border-white/10"
                    >
                        Rescan Library
                    </button>
                    <button
                        onClick={() => navigate('/search')}
                        className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors"
                    >
                        + Add New
                    </button>
                </div>
            </div>

            <WatchlistManager />

            <ConfirmModal
                isOpen={showRescanModal}
                onClose={() => setShowRescanModal(false)}
                onConfirm={handleRescan}
                title="Rescan Library"
                message="This will check for missing files and re-queue them for download. Are you sure?"
                confirmText="Rescan"
            />
        </div>
    )
}
