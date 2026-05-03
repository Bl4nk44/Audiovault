import { RefreshCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "../../hooks/useTranslation";
import api from "../../services/api";
import { type WatchlistItem } from "../../types";
import { notify as toast } from "../../utils/notify";

interface WatchlistItemProps {
  item: WatchlistItem;
  onRemove: (id: string) => void;
  onSync?: (item: WatchlistItem) => void;
  viewMode?: "list" | "grid";
}

const AutoDownloadSwitch = ({
  autoDownload,
  onToggle,
}: {
  autoDownload: boolean;
  onToggle: (e: React.MouseEvent) => void;
}) => (
  <button
    onClick={onToggle}
    className={`relative w-11 h-6 rounded-full transition-all duration-300 flex items-center cursor-pointer border ${
      autoDownload
        ? "bg-green-500/20 border-green-500 shadow-[0_0_10px_rgba(34,197,94,0.4)]"
        : "bg-red-500/20 border-red-500 shadow-[0_0_10px_rgba(239,68,68,0.4)]"
    }`}
    title={autoDownload ? "Auto-download: ON" : "Auto-download: OFF"}
  >
    <div
      className={`absolute w-4 h-4 rounded-full shadow-sm transform transition-all duration-300 ${
        autoDownload ? "translate-x-6 bg-green-400" : "translate-x-1 bg-red-400"
      }`}
    />
  </button>
);

export default function WatchlistItem({
  item,
  onRemove,
  onSync,
  viewMode = "list",
}: Readonly<WatchlistItemProps>) {
  const { t } = useTranslation();
  const navigate = useNavigate();
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

  // ... inside component ...
  const handleCardClick = () => {
    if (item.watch_type === "artist" && item.source_id) {
      navigate(`/artist/${item.source_id}`);
    } else if (item.watch_type === "playlist") {
      navigate(`/library?source=${item.source}&playlist=${encodeURIComponent(item.source_name)}`);
    } else if (item.watch_type === "channel") {
      navigate(`/library?source=${item.source}&playlist=${encodeURIComponent(item.source_name)}`);
    }
  };

  const imageUrl = item.metadata_content?.image_url;

  // Helper for the Toggle Switch

  if (viewMode === "grid") {
    return (
      <button
        onClick={handleCardClick}
        className="text-left w-full group relative bg-card border border-border rounded-xl overflow-hidden hover:border-primary/50 transition-all hover:shadow-lg hover:shadow-primary/5 aspect-square cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-primary"
      >
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

          {/* Top Right Badges */}
          <div className="absolute top-2 right-2 z-20 pointer-events-none flex flex-col items-end gap-2">
            {item.new_items_count > 0 && (
              <div className="bg-primary text-black text-xs font-bold px-2 py-1 rounded-full shadow-lg">
                {item.new_items_count} {t("watchlist.newItems")}
              </div>
            )}
            <span className="capitalize px-2 py-0.5 rounded-full bg-black/60 border border-white/10 backdrop-blur-md text-xs text-white shadow-sm">
              {item.watch_type}
            </span>
          </div>

          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-linear-to-t from-black/90 via-black/40 to-transparent opacity-60 group-hover:opacity-80 transition-opacity" />

          {/* Center Overlay Actions (Sync & Delete only) */}
          <div className="absolute inset-0 flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity z-10">
            {onSync && item.watch_type === "playlist" && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSync(item);
                }}
                className="p-3 rounded-full bg-secondary/80 text-foreground hover:bg-white hover:text-black transition-colors cursor-pointer"
                title={t("watchlist.syncDeletions")}
              >
                <RefreshCcw size={20} />
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRemove(item.id);
              }}
              className="p-3 rounded-full bg-secondary/80 text-foreground hover:bg-destructive/80 hover:text-white transition-colors cursor-pointer"
              title={t("watchlist.removeFromWatchlist")}
            >
              <Trash2 size={20} />
            </button>
          </div>
        </div>

        {/* Bottom Info & Switch */}
        <div className="absolute bottom-0 left-0 right-0 p-4 z-10 pointer-events-none flex items-end justify-between gap-2">
          <div className="min-w-0">
            <h4 className="font-bold truncate text-white mb-0.5 shadow-black drop-shadow-md group-hover:text-primary transition-colors">
              {item.source_name}
            </h4>
            <span className="text-xs text-gray-300 capitalize drop-shadow-md block">
              {item.source}
            </span>
          </div>

          <div role="none" className="pointer-events-auto shrink-0 pb-0.5" onClick={(e) => e.stopPropagation()}>
            <AutoDownloadSwitch autoDownload={autoDownload} onToggle={toggleAutoDownload} />
          </div>
        </div>
      </button>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4 flex items-center justify-between group hover:border-primary/50 transition-colors">
      <div className="flex items-center gap-4 min-w-0">
        <button
          onClick={handleCardClick}
          className="w-12 h-12 rounded overflow-hidden bg-secondary shrink-0 cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-primary"
          title={t("watchlist.viewDetails", "View details")}
        >
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
        </button>

        <div className="min-w-0">
          <button
            onClick={handleCardClick}
            className="font-medium truncate cursor-pointer hover:text-primary hover:underline focus:outline-hidden focus:ring-1 focus:ring-primary text-left"
            title={item.source_name}
          >
            {item.source_name}
          </button>
          <p className="text-sm text-muted-foreground capitalize">
            {item.source} • {item.watch_type}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4 shrink-0">
        <div role="none" onClick={(e) => e.stopPropagation()}>
          <AutoDownloadSwitch autoDownload={autoDownload} onToggle={toggleAutoDownload} />
        </div>

        {item.new_items_count > 0 && (
          <span className="bg-primary text-primary-foreground text-xs px-2 py-1 rounded-full pointer-events-none">
            {item.new_items_count} {t("watchlist.newItems")}
          </span>
        )}

        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove(item.id);
          }}
          className="p-2 text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
          title={t("watchlist.removeFromWatchlist")}
        >
          <Trash2 size={18} />
        </button>
        {onSync && item.watch_type === "playlist" && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSync(item);
            }}
            className="p-2 text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
            title={t("watchlist.syncDeletions")}
          >
            <RefreshCcw size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
