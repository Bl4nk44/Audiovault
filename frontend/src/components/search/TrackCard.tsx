import { motion } from "framer-motion";
import { AudioLines, Download, ListPlus, Music, Play, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
import { type Track } from "../../types";
import { notify as toast } from "../../utils/notify";
import AddToPlaylistModal from "../AddToPlaylistModal";

interface TrackCardProps {
  track: Track;
  queue?: Track[];
  onRemove?: () => void;
}

export default function TrackCard({ track, queue, onRemove }: Readonly<TrackCardProps>) {
  const navigate = useNavigate();
  const { playTrack, currentTrack, isPlaying, togglePlay } = useStore();
  const [showPlaylistModal, setShowPlaylistModal] = useState(false);

  const isCurrentTrack =
    currentTrack?.id !== undefined &&
    (currentTrack?.id === track.id || (track.spotify_id && currentTrack?.id === track.spotify_id));
  const isNowPlaying = isCurrentTrack && isPlaying;

  const handleArtistClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const artistId = track.artist_id || track.spotify_artist_id;
    if (artistId) {
      navigate(`/artist/${artistId}`);
    }
  };

  const handlePlay = () => {
    if (isCurrentTrack) {
      togglePlay();
      return;
    }

    playTrack(
      {
        id: track.id,
        title: track.title,
        artist: track.artist,
        cover: track.cover,
        source: track.source,
        duration_ms: track.duration_ms,
      },
      queue
    );
  };

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.post("/downloads/add", {
        track_id: track.id,
        source: track.source,
      });
      toast.success("Added to download queue");
    } catch {
      toast.error("Failed to add to queue");
    }
  };

  const handleOpenPlaylistModal = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowPlaylistModal(true);
  };

  const formatDuration = (ms: number) => {
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(0);
    return `${minutes}:${Number(seconds) < 10 ? "0" : ""}${seconds}`;
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        onClick={handlePlay}
        data-testid="track-card"
        className={`w-full p-3 rounded-xl cursor-pointer border overflow-hidden backdrop-blur-xl transition-all duration-200 group ${
          isCurrentTrack
            ? "bg-white/10 border-primary/50 shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]"
            : "bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10"
        }`}
      >
        {/* Main Row */}
        <div className="flex items-center gap-4">
          {/* Cover Image */}
          <div className="relative w-14 h-14 rounded-lg overflow-hidden shrink-0 shadow-lg group-hover:shadow-primary/20 transition-all">
            {track.cover || track.image_url ? (
              <img
                src={track.cover || track.image_url}
                alt={track.title}
                className={`w-full h-full object-cover transition-opacity ${
                  isNowPlaying ? "opacity-40" : ""
                }`}
              />
            ) : (
              <div className="w-full h-full bg-linear-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                <Music className={`${isCurrentTrack ? "text-primary" : "text-gray-600"}`} />
              </div>
            )}

            {/* Center Play Icon Overlay */}
            <div
              className={`absolute inset-0 flex items-center justify-center transition-opacity ${
                isCurrentTrack ? "opacity-100" : "opacity-0 group-hover:opacity-100 bg-black/40"
              }`}
            >
              {(() => {
                if (isNowPlaying) return <AudioLines className="text-primary animate-pulse" size={20} />;
                if (isCurrentTrack) return <Play className="text-primary fill-primary" size={20} />;
                return <Play className="text-white fill-white" size={20} />;
              })()}
            </div>
          </div>

          {/* Content info */}
          <div className="flex-1 min-w-0 flex flex-col justify-center">
            <h3
              className={`font-bold text-base leading-tight truncate pr-2 ${
                isCurrentTrack ? "text-primary" : "text-white"
              }`}
              title={track.title}
            >
              {track.title}
            </h3>
            <button
              onClick={handleArtistClick}
              className={`text-sm text-left truncate transition-colors ${
                track.artist_id || track.spotify_artist_id
                  ? "text-gray-400 hover:text-white hover:underline decoration-white/50"
                  : "text-gray-400 cursor-default"
              }`}
              title={track.artist}
            >
              {track.artist}
            </button>
          </div>

          {/* Right Side: Duration & Actions */}
          <div className="shrink-0 flex flex-col items-end gap-2">
            {/* Duration */}
            <span className="text-xs font-medium text-gray-500 bg-black/20 px-2 py-0.5 rounded-full">
              {formatDuration(track.duration_ms || 0)}
            </span>

            {/* Actions Icons */}
            <div className="flex items-center gap-1">
              {/* Add to Playlist */}
              <button
                onClick={handleOpenPlaylistModal}
                className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                title="Add to Playlist"
              >
                <ListPlus size={18} />
              </button>

              {/* Download */}
              <button
                onClick={handleDownload}
                className="p-1.5 text-primary/80 hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                title="Download"
              >
                <Download size={18} />
              </button>

              {/* Remove */}
              {onRemove && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove();
                  }}
                  className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                  title="Remove"
                >
                  <Trash2 size={18} />
                </button>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      <AddToPlaylistModal
        isOpen={showPlaylistModal}
        onClose={() => setShowPlaylistModal(false)}
        trackIds={
          track.id
            ? [track.id]
            : [`external:${track.artist}:${track.title}`]
        }
      />
    </>
  );
}
