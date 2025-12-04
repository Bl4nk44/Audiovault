import WatchlistManager from '../components/watchlist/WatchlistManager'

import { useNavigate } from 'react-router-dom'

export default function Watchlist() {
    const navigate = useNavigate()

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
                    <p className="text-muted-foreground">Track new releases from your favorite artists and channels.</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={async () => {
                            try {
                                const api = (await import('../services/api')).default
                                const res = await api.post('/downloads/rescan')
                                alert(`Rescan complete. Found ${res.data.rescanned_count} missing files. They have been re-queued.`)
                            } catch (e) {
                                console.error("Rescan failed", e)
                                alert("Rescan failed")
                            }
                        }}
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
        </div>
    )
}
