import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Music,
  ListMusic,
  Loader2,
  Plus,
  Check,
  PlayCircle,
  Clock,
} from "lucide-react";
import { playlistsApi } from "../api/playlists";
import Button from "../components/ui/Button";
import { useStore } from "../store/useStore";
import { notify as toast } from "../utils/notify";
import TrackCard from "../components/search/TrackCard";
import { isValidImageUrl } from "../utils/validation";

export default function PlaylistDetails() {
  const { id } = useParams<{ id: string }>();
  // Retrieve source from state passed via navigation, default to spotify
  const location = useLocation();
  const source = location.state?.source || "spotify";

  const navigate = useNavigate();
  const { watchlist, addToWatchlist, removeFromWatchlist } = useStore();

  const {
    data: playlist,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["playlist", id, source],
    queryFn: () => playlistsApi.getById(id!, source),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !playlist) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <p className="text-red-400">Failed to load playlist</p>
        <Button onClick={() => navigate(-1)} variant="outline">
          Go Back
        </Button>
      </div>
    );
  }

  const heroImage = isValidImageUrl(playlist.image_url)
    ? playlist.image_url
    : null;

  const isWatched = watchlist.some((item) => item.source_id === playlist.id);
  const watchedItem = watchlist.find((item) => item.source_id === playlist.id);

  const handleWatchlistToggle = () => {
    if (isWatched && watchedItem) {
      removeFromWatchlist(watchedItem.id);
      toast.success("Removed from watchlist");
    } else {
      addToWatchlist({
        source: source,
        source_id: playlist.id,
        source_name: playlist.title,
        watch_type: "playlist",
        auto_download: true,
        new_items_count: 0,
        metadata_content: { image_url: heroImage || undefined },
      });
      toast.success("Added to watchlist");
    }
  };

  const totalDurationMs =
    playlist.tracks?.reduce(
      (acc, track) => acc + (track.duration_ms || 0),
      0
    ) || 0;
  const totalDurationMinutes = Math.floor(totalDurationMs / 60000);
  const totalDurationHours = Math.floor(totalDurationMinutes / 60);

  return (
    <div className="space-y-8 pb-10">
      {/* Hero Section */}
      <div className="relative h-64 md:h-80 rounded-3xl overflow-hidden group">
        {heroImage ? (
          <img
            src={heroImage}
            alt={playlist.title}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full bg-linear-to-br from-gray-800 to-gray-900 flex items-center justify-center">
            <ListMusic className="w-24 h-24 text-gray-700" />
          </div>
        )}
        <div className="absolute inset-0 bg-linear-to-t from-black/90 via-black/40 to-transparent flex flex-col justify-end p-8">
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-4 left-4 text-white hover:bg-white/10"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="w-6 h-6" />
          </Button>

          <div className="absolute top-4 right-4">
            <Button
              variant={isWatched ? "secondary" : "primary"}
              onClick={handleWatchlistToggle}
              className="gap-2"
            >
              {isWatched ? <Check size={16} /> : <Plus size={16} />}
              {isWatched ? "Following" : "Follow"}
            </Button>
          </div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-6xl font-bold text-white mb-2"
          >
            {playlist.title}
          </motion.h1>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="flex items-center gap-4 text-gray-300"
          >
            <span className="bg-white/10 px-3 py-1 rounded-full text-sm capitalize flex items-center gap-2">
              {source === "spotify" && (
                <img
                  src="/spotify-icon.svg"
                  alt="Spotify"
                  title="Spotify"
                  className="w-4 h-4"
                  onError={(e) => (e.currentTarget.style.display = "none")}
                />
              )}
              {source === "youtube" && (
                <img
                  src="/youtube-icon.svg"
                  alt="YouTube"
                  title="YouTube"
                  className="w-4 h-4"
                  onError={(e) => (e.currentTarget.style.display = "none")}
                />
              )}
              {source}
            </span>
            {playlist.tracks && (
              <span className="flex items-center gap-1 text-sm">
                <Music size={14} /> {playlist.tracks.length} tracks
              </span>
            )}
            {totalDurationMinutes > 0 && (
              <span className="flex items-center gap-1 text-sm">
                <Clock size={14} />
                {totalDurationHours > 0 ? `${totalDurationHours} hr ` : ""}
                {totalDurationMinutes % 60} min
              </span>
            )}
          </motion.div>

          {playlist.description && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-gray-400 mt-2 max-w-2xl line-clamp-2"
            >
              {playlist.description}
            </motion.p>
          )}
        </div>
      </div>

      {/* Tracks Section */}
      {playlist.tracks && playlist.tracks.length > 0 ? (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <PlayCircle className="w-6 h-6 text-primary" />
            Tracks
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {playlist.tracks.map((track) => (
              <TrackCard
                key={track.id}
                track={{
                  ...track,
                  source: source,
                  // Ensure cover is present if available in track, otherwise fallback to playlist cover
                  cover: track.image_url || heroImage || undefined,
                }}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-20 text-gray-500">
          <Music className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No tracks found in this playlist.</p>
        </div>
      )}
    </div>
  );
}
