import { useEffect, useState } from "react";
import { useStore } from "../../store/useStore";
import WatchlistItem from "./WatchlistItem";
import { Loader2, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import api from "../../services/api";

import { LayoutGrid, List } from "lucide-react";

export default function WatchlistManager() {
  const { watchlist, syncWatchlist, removeFromWatchlist } = useStore();
  const [isLoading, setIsLoading] = useState(true);
  const [isChecking, setIsChecking] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "grid">("grid");

  useEffect(() => {
    syncWatchlist().finally(() => setIsLoading(false));
  }, [syncWatchlist]);

  const handleRemove = async (id: string) => {
    try {
      await removeFromWatchlist(id);
      toast.success("Removed from watchlist");
    } catch (error) {
      toast.error("Failed to remove item");
    }
  };

  const handleCheckUpdates = async () => {
    setIsChecking(true);
    try {
      const res = await api.post("/watchlist/check-updates");
      toast.success(
        `Check complete. ${res.data.new_downloads} new items found.`
      );
      syncWatchlist(); // Refresh list to update counts/dates
    } catch (error) {
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
        <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
          <button
            onClick={() => setViewMode("list")}
            className={`p-2 rounded-md transition-all ${
              viewMode === "list"
                ? "bg-white/10 text-white shadow-sm"
                : "text-gray-400 hover:text-white"
            }`}
            title="List View"
          >
            <List size={18} />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={`p-2 rounded-md transition-all ${
              viewMode === "grid"
                ? "bg-white/10 text-white shadow-sm"
                : "text-gray-400 hover:text-white"
            }`}
            title="Grid View"
          >
            <LayoutGrid size={18} />
          </button>
        </div>

        <button
          onClick={handleCheckUpdates}
          disabled={isChecking}
          className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
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
            Your watchlist is empty. Add artists or playlists to track new
            releases.
          </div>
        ) : (
          watchlist.map((item) => (
            <WatchlistItem
              key={item.id}
              item={item}
              onRemove={handleRemove}
              viewMode={viewMode}
            />
          ))
        )}
      </div>
    </div>
  );
}
