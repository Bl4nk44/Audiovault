import { Plus, Check, ListMusic } from "lucide-react";
import api from "../../services/api";
import { notify as toast } from "../../utils/notify";
import { motion } from "framer-motion";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Playlist } from "../../types";

interface PlaylistCardProps {
  playlist: Playlist;
}

export default function PlaylistCard({ playlist }: PlaylistCardProps) {
  const [isAdded, setIsAdded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const navigate = useNavigate();

  const handleAddToWatchlist = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.post("/watchlist/add", {
        watch_type: "playlist",
        source: playlist.source,
        source_id: playlist.id,
        source_name: playlist.title,
        image_url: playlist.image_url,
        auto_download: true, // Default to true
      });
      setIsAdded(true);
      toast.success("Playlist added to watchlist");
    } catch {
      toast.error("Failed to add to watchlist");
    }
  };

  const handleClick = () => {
    navigate(`/playlist/${playlist.id}`, {
      state: { source: playlist.source },
    });
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02, backgroundColor: "rgba(255, 255, 255, 0.1)" }}
      onClick={handleClick}
      className="group relative flex flex-col p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-all cursor-pointer"
    >
      <div className="relative w-full aspect-square rounded-lg overflow-hidden shadow-lg group-hover:shadow-primary/20 transition-all mb-4">
        {playlist.image_url && !imageError ? (
          <img
            src={playlist.image_url}
            alt={playlist.title}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full bg-linear-to-br from-gray-800 to-gray-900 flex items-center justify-center">
            <ListMusic className="text-gray-600" size={40} />
          </div>
        )}
      </div>

      <h3 className="font-bold text-white truncate group-hover:text-primary transition-colors text-center w-full">
        {playlist.title}
      </h3>
      <div className="flex justify-between items-center mt-1 w-full px-1">
        <div className="flex items-center gap-1.5">
          {playlist.source === "spotify" && (
            <img
              src="/spotify-icon.svg"
              title="Spotify"
              className="w-4 h-4"
              onError={(e) => (e.currentTarget.style.display = "none")}
            />
          )}
          {playlist.source === "youtube" && (
            <img
              src="/youtube-icon.svg"
              title="YouTube"
              className="w-4 h-4"
              onError={(e) => (e.currentTarget.style.display = "none")}
            />
          )}
          <p className="text-sm text-gray-400 capitalize">{playlist.source}</p>
        </div>
        {playlist.tracks_count && (
          <span className="text-xs text-gray-500">
            {playlist.tracks_count} tracks
          </span>
        )}
      </div>

      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={handleAddToWatchlist}
        disabled={isAdded}
        className={`mt-4 mx-auto p-3 rounded-full transition-colors shadow-lg ${
          isAdded
            ? "bg-green-500 text-black"
            : "bg-white/10 text-white hover:bg-primary hover:text-black border border-white/10"
        }`}
        title={isAdded ? "Added" : "Add to Watchlist"}
      >
        {isAdded ? <Check size={24} /> : <Plus size={24} />}
      </motion.button>
    </motion.div>
  );
}
