import { useEffect, useState } from 'react'
import { getWatchlist, removeFromWatchlist } from '../../services/watchlist'
import WatchlistItem from './WatchlistItem'
import { Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

export default function WatchlistManager() {
    const [watchlist, setWatchlist] = useState<any[]>([])
    const [isLoading, setIsLoading] = useState(true)

    const fetchWatchlist = async () => {
        try {
            const data = await getWatchlist()
            setWatchlist(data)
        } catch (error) {
            toast.error('Failed to load watchlist')
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchWatchlist()
    }, [])

    const handleRemove = async (id: string) => {
        try {
            await removeFromWatchlist(id)
            setWatchlist(prev => prev.filter(item => item.id !== id))
            toast.success('Removed from watchlist')
        } catch (error) {
            toast.error('Failed to remove item')
        }
    }

    if (isLoading) {
        return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>
    }

    return (
        <div className="space-y-6">
            <div className="grid gap-4">
                {watchlist.length === 0 ? (
                    <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-lg">
                        Your watchlist is empty. Add artists or playlists to track new releases.
                    </div>
                ) : (
                    watchlist.map((item) => (
                        <WatchlistItem key={item.id} item={item} onRemove={handleRemove} />
                    ))
                )}
            </div>
        </div>
    )
}
