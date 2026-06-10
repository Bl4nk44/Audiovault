import { LayoutGrid, List, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
import { type WatchlistItem as WatchlistItemType } from "../../types";
import { notify as toast } from "../../utils/notify";
import SyncModal from "../sync/SyncModal";
import WatchlistItem from "./WatchlistItem";

export default function WatchlistManager() {
  const { watchlist, syncWatchlist, removeFromWatchlist } = useStore();
  const [isLoading, setIsLoading] = useState(true);
  const [isChecking, setIsChecking] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "grid">(
    () => (localStorage.getItem("watchlist:viewMode") as "list" | "grid") || "grid"
  );

  const handleSetViewMode = (mode: "list" | "grid") => {
    localStorage.setItem("watchlist:viewMode", mode);
    setViewMode(mode);
  };
  const [selectedSyncItem, setSelectedSyncItem] = useState<WatchlistItemType | null>(null);

  useEffect(() => {
    syncWatchlist().finally(() => setIsLoading(false));
  }, [syncWatchlist]);

  const handleRemove = async (id: string) => {
    try {
      await removeFromWatchlist(id);
      toast.success("Removed from watchlist");
    } catch {
      toast.error("Failed to remove item");
    }
  };

  const handleSync = (item: WatchlistItemType) => {
    setSelectedSyncItem(item);
  };

  const handleCheckUpdates = async () => {
    setIsChecking(true);
    try {
      const res = await api.post("/watchlist/check-updates");
      toast.success(`Check complete. ${res.data.new_downloads} new items found.`);
      syncWatchlist(); // Refresh list to update counts/dates
    } catch {
      toast.error("Failed to check for updates");
    } finally {
      setIsChecking(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex bg-card/40 rounded-lg p-1 border border-border">
          <button
            onClick={() => handleSetViewMode("grid")}
            className={`p-2 rounded-md transition-all cursor-pointer ${
              viewMode === "grid"
                ? "bg-secondary text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="Grid View"
          >
            <LayoutGrid size={18} />
          </button>
          <button
            onClick={() => handleSetViewMode("list")}
            className={`p-2 rounded-md transition-all cursor-pointer ${
              viewMode === "list"
                ? "bg-secondary text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="List View"
          >
            <List size={18} />
          </button>
        </div>

        <button
          onClick={handleCheckUpdates}
          disabled={isChecking}
          className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw size={16} className={isChecking ? "animate-spin" : ""} />
          {isChecking ? "Checking..." : "Check for Updates"}
        </button>
      </div>

      <div
        className={
          viewMode === "grid"
            ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6"
            : "grid gap-4"
        }
      >
        {watchlist.length === 0 ? (
          <div className="col-span-full text-center py-12 text-muted-foreground border border-dashed border-border rounded-lg">
            Your watchlist is empty. Add artists or playlists to track new releases.
          </div>
        ) : (
          watchlist.map((item) => (
            <WatchlistItem
              key={item.id}
              item={item}
              onRemove={handleRemove}
              onSync={handleSync}
              viewMode={viewMode}
            />
          ))
        )}
      </div>

      <SyncModal item={selectedSyncItem} onClose={() => setSelectedSyncItem(null)} />
    </div>
  );
}
