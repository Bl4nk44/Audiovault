import { Trash2, DownloadCloud, RefreshCcw } from "lucide-react";
import { useState } from "react";
import api from "../../services/api";
import toast from "react-hot-toast";
import { type WatchlistItem } from "../../types";

interface WatchlistItemProps {
  item: WatchlistItem;
  onRemove: (id: string) => void;
  onSync?: (item: WatchlistItem) => void;
  viewMode?: "list" | "grid";
}

export default function WatchlistItem({
  item,
  onRemove,
  onSync,
  viewMode = "list",
}: WatchlistItemProps) {
  const [autoDownload, setAutoDownload] = useState(item.auto_download);
  const [imageError, setImageError] = useState(false);

  const toggleAutoDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const newValue = !autoDownload;
    setAutoDownload(newValue);
    try {
      await api.patch(`/watchlist/${item.id}`, { auto_download: newValue });
      toast.success(`Auto-download ${newValue ? "enabled" : "disabled"}`);
    } catch {
      setAutoDownload(!newValue);
      toast.error("Failed to update settings");
    }
  };

  const imageUrl = item.metadata_content?.image_url;

  if (viewMode === "grid") {
    return (
      <div className="group relative bg-card border border-border rounded-xl overflow-hidden hover:border-primary/50 transition-all hover:shadow-lg hover:shadow-primary/5 aspect-square">
        <div className="absolute inset-0">
          {imageUrl && !imageError ? (
            <img
              src={imageUrl}
              alt={item.source_name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full bg-secondary flex items-center justify-center text-4xl font-bold text-muted-foreground uppercase">
              {item.source?.[0] || "?"}
            </div>
          )}

          {/* Gradient Overlay for Text Readability */}
          <div className="absolute inset-0 bg-linear-to-t from-black/90 via-black/40 to-transparent opacity-60 group-hover:opacity-80 transition-opacity" />

          {/* Overlay Actions */}
          <div className="absolute inset-0 flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            <button
              onClick={toggleAutoDownload}
              className={`p-3 rounded-full transition-colors ${
                autoDownload
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary/80 text-foreground hover:bg-secondary"
              }`}
              title={
                autoDownload ? "Auto-download enabled" : "Enable auto-download"
              }
            >
              <DownloadCloud size={20} />
            </button>
            {onSync && item.watch_type === "playlist" && (
              <button
                onClick={() => onSync(item)}
                className="p-3 rounded-full bg-secondary/80 text-foreground hover:bg-white hover:text-black transition-colors"
                title="Sync Deletions"
              >
                <RefreshCcw size={20} />
              </button>
            )}
            <button
              onClick={() => onRemove(item.id)}
              className="p-3 rounded-full bg-secondary/80 text-foreground hover:bg-destructive/80 hover:text-white transition-colors"
              title="Remove from watchlist"
            >
              <Trash2 size={20} />
            </button>
          </div>

          {item.new_items_count > 0 && (
            <div className="absolute top-2 right-2 bg-primary text-black text-xs font-bold px-2 py-1 rounded-full shadow-lg z-20">
              {item.new_items_count} new
            </div>
          )}
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 z-10">
          <h4 className="font-bold truncate text-white mb-1 shadow-black drop-shadow-md">
            {item.source_name}
          </h4>
          <div className="flex items-center justify-between text-xs text-gray-300">
            <span className="capitalize drop-shadow-md">{item.source}</span>
            <span className="capitalize px-2 py-0.5 rounded-full bg-white/10 border border-white/10 backdrop-blur-sm">
              {item.watch_type}
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4 flex items-center justify-between group hover:border-primary/50 transition-colors">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded overflow-hidden bg-secondary shrink-0">
          {imageUrl && !imageError ? (
            <img
              src={imageUrl}
              alt={item.source_name}
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xl font-bold text-muted-foreground uppercase">
              {item.source?.[0] || "?"}
            </div>
          )}
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
          className={`p-2 rounded-full transition-colors ${
            autoDownload
              ? "bg-primary/20 text-primary"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
          title={
            autoDownload ? "Auto-download enabled" : "Enable auto-download"
          }
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
        {onSync && item.watch_type === "playlist" && (
          <button
            onClick={() => onSync(item)}
            className="p-2 text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
            title="Sync Deletions"
          >
            <RefreshCcw size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
