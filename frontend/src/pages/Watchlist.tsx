import WatchlistManager from '../components/watchlist/WatchlistManager'

export default function Watchlist() {
    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
                    <p className="text-muted-foreground">Track new releases from your favorite artists and channels.</p>
                </div>
                <button className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors">
                    + Add New
                </button>
            </div>

            <WatchlistManager />
        </div>
    )
}
