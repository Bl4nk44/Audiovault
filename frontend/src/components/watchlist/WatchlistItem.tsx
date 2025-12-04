import { Trash2, DownloadCloud } from 'lucide-react'
import { useState } from 'react'
import api from '../../services/api'
import toast from 'react-hot-toast'

interface WatchlistItemProps {
    item: {
        id: string
        source_name: string
        source: string
        watch_type: string
        new_items_count: number
        last_checked_at: string
        auto_download: boolean
    }
    onRemove: (id: string) => void
}

export default function WatchlistItem({ item, onRemove }: WatchlistItemProps) {
    const [autoDownload, setAutoDownload] = useState(item.auto_download)

    const toggleAutoDownload = async () => {
        const newValue = !autoDownload
        setAutoDownload(newValue)
        try {
            await api.patch(`/watchlist/${item.id}`, { auto_download: newValue })
            toast.success(`Auto-download ${newValue ? 'enabled' : 'disabled'}`)
        } catch (error) {
            setAutoDownload(!newValue)
            toast.error('Failed to update settings')
        }
    }
    return (
        <div className="bg-card border border-border rounded-lg p-4 flex items-center justify-between group hover:border-primary/50 transition-colors">
            <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-secondary rounded flex items-center justify-center text-xl font-bold text-muted-foreground uppercase">
                    {item.source[0]}
                </div>

                <div>
                    <h4 className="font-medium">{item.source_name}</h4>
                    <p className="text-sm text-muted-foreground capitalize">
                        {item.source} • {item.watch_type}
                    </p>
                </div>
            </div>

            <div className="flex items-center gap-4">
                <button
                    onClick={toggleAutoDownload}
                    className={`p-2 rounded-full transition-colors ${autoDownload ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground hover:text-white'
                        }`}
                    title={autoDownload ? "Auto-download enabled" : "Enable auto-download"}
                >
                    <DownloadCloud size={18} />
                </button>
                {item.new_items_count > 0 && (
                    <span className="bg-primary text-primary-foreground text-xs px-2 py-1 rounded-full">
                        {item.new_items_count} new
                    </span>
                )}

                <button
                    onClick={() => onRemove(item.id)}
                    className="p-2 text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                    title="Remove from watchlist"
                >
                    <Trash2 size={18} />
                </button>
            </div>
        </div>
    )
}
