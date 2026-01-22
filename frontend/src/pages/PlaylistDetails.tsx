import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Check,
  Clock,
  Download,
  Edit2,
  ListMusic,
  Loader2,
  Music,
  PlayCircle,
  Plus,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { playlistsApi } from "../api/playlists";
import TrackCard from "../components/search/TrackCard";
import Button from "../components/ui/Button";
import ConfirmModal from "../components/ui/ConfirmModal";
import { useStore } from "../store/useStore";
import { notify as toast } from "../utils/notify";
import { isValidImageUrl } from "../utils/validation";

export default function PlaylistDetails() {
  const { id } = useParams<{ id: string }>();
  // Retrieve source from state passed via navigation, default to spotify
  const location = useLocation();
  const source = location.state?.source || "spotify";

  const navigate = useNavigate();
  const { watchlist, addToWatchlist, removeFromWatchlist } = useStore();
  const queryClient = useQueryClient();

  // Local state for modals
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editName, setEditName] = useState("");
  const [trackToDelete, setTrackToDelete] = useState<string | null>(null);

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

  const heroImage = isValidImageUrl(playlist.image_url) ? playlist.image_url : null;

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

  const handleExportJson = async () => {
    if (source !== "local" || !id) {
      toast.error("Export is only available for local playlists");
      return;
    }
    try {
      await playlistsApi.exportAsJson(id, playlist.title);
      toast.success("Playlist exported successfully");
    } catch {
      toast.error("Failed to export playlist");
    }
  };

  const handleDeletePlaylist = async () => {
    if (!id) return;
    try {
      await playlistsApi.delete(id);
      toast.success("Playlist deleted");
      navigate("/library");
    } catch {
      toast.error("Failed to delete playlist");
    }
  };

  const handleUpdatePlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !editName.trim()) return;
    try {
      await playlistsApi.update(id, { name: editName });
      toast.success("Playlist updated");
      setShowEditModal(false);
      queryClient.invalidateQueries({ queryKey: ["playlist", id, source] });
    } catch {
      toast.error("Failed to update playlist");
    }
  };

  const handleRemoveTrack = async (trackId: string) => {
    if (!id) return;
    try {
      // Assuming removeTracks takes an array
      await playlistsApi.removeTracks(id, [trackId]);
      toast.success("Track removed from playlist");
      queryClient.invalidateQueries({ queryKey: ["playlist", id, source] });
      setTrackToDelete(null);
    } catch {
      toast.error("Failed to remove track");
    }
  };

  const totalDurationMs =
    playlist.tracks?.reduce((acc, track) => acc + (track.duration_ms || 0), 0) || 0;
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

          <div className="absolute top-4 right-4 flex gap-2">
            {source === "local" && (
              <Button
                variant="outline"
                onClick={handleExportJson}
                className="gap-2 bg-white/10 hover:bg-white/20 text-white border-white/20"
              >
                <Download size={16} />
                Export JSON
              </Button>
            )}
            {source === "local" && (
              <>
                <Button
                  variant="outline"
                  onClick={() => {
                    setEditName(playlist.title);
                    setShowEditModal(true);
                  }}
                  className="gap-2 bg-white/10 hover:bg-white/20 text-white border-white/20"
                >
                  <Edit2 size={16} />
                  Edit
                </Button>
                <Button
                  variant="danger"
                  onClick={() => setShowDeleteModal(true)}
                  className="gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border-red-500/20"
                >
                  <Trash2 size={16} />
                  Delete
                </Button>
              </>
            )}
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
                onRemove={
                  source === "local"
                    ? () => setTrackToDelete(track.id) // Or track.track_id depending on structure?
                    : // Note: playlistsApi.getLocalById maps backend tracks to frontend Track, keeping 'id'.
                      // backend: track_id -> frontend: id. So we pass track.id.
                      undefined
                }
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

      {/* Delete Playlist Modal */}
      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeletePlaylist}
        title="Delete Playlist"
        message={`Are you sure you want to delete "${playlist.title}"? This cannot be undone.`}
        confirmText="Delete Playlist"
        variant="danger"
      />

      {/* Remove Track Modal */}
      <ConfirmModal
        isOpen={!!trackToDelete}
        onClose={() => setTrackToDelete(null)}
        onConfirm={() => trackToDelete && handleRemoveTrack(trackToDelete)}
        title="Remove Track"
        message="Are you sure you want to remove this track from the playlist?"
        confirmText="Remove"
        variant="danger"
      />

      {/* Edit Modal (Inline for simplicity) */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-card border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl"
          >
            <h2 className="text-xl font-bold text-foreground mb-4">Edit Playlist</h2>
            <form onSubmit={handleUpdatePlaylist} className="space-y-4">
              <div>
                <label
                  htmlFor="playlistName"
                  className="block text-sm font-medium text-muted-foreground mb-1"
                >
                  Name
                </label>
                <input
                  id="playlistName"
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-secondary/30 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  autoFocus
                />
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <Button type="button" variant="ghost" onClick={() => setShowEditModal(false)}>
                  Cancel
                </Button>
                <Button type="submit">Save Changes</Button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
}
