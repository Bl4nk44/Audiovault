import { useNavigate } from "react-router-dom";
import WatchlistManager from "../components/watchlist/WatchlistManager";

export default function Watchlist() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
          <p className="text-muted-foreground">
            Track new releases from your favorite artists and channels.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate("/search")}
            className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors cursor-pointer"
          >
            + Add New
          </button>
        </div>
      </div>

      <WatchlistManager />
    </div>
  );
}
