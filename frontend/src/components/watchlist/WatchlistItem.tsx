import { Trash2 } from 'lucide-react'

interface WatchlistItemProps {
    item: {
        id: string
        source_name: string
        source: string
        watch_type: string
        new_items_count: number
        last_checked_at: string
    }
    onRemove: (id: string) => void
}

export default function WatchlistItem({ item, onRemove }: WatchlistItemProps) {
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
