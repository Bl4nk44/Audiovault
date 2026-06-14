import React, { useState } from "react";
import { useTranslation } from "../../hooks/useTranslation";
import { IoAdd, IoPlay } from "react-icons/io5";
import type { RecommendedTrack } from "../../types/lastfm";
import AddToPlaylistModal from "../AddToPlaylistModal";

interface RecommendationCardProps {
  track: RecommendedTrack;
  onPlay: (track: RecommendedTrack) => void;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({ track, onPlay }) => {
  const { t } = useTranslation();
  const [showPlaylistModal, setShowPlaylistModal] = useState(false);

  // Add methods to search this track in Audiovault and play it.
  // For now we assume we pass the track object up.

  return (
    <>
      <div className="group relative bg-card/50 hover:bg-secondary transition-all duration-300 rounded-xl overflow-hidden border border-white/5 hover:border-primary/30">
        {/* Image / Cover */}
        <div className="relative aspect-square w-full bg-secondary overflow-hidden">
          {track.image_url ? (
            <img
              src={track.image_url}
              alt={track.name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-secondary text-zinc-600">
              <span className="text-4xl font-bold opacity-20">{track.name[0]}</span>
            </div>
          )}

          {/* Hover Overlay */}
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4">
            <button
              onClick={() => onPlay(track)}
              className="w-12 h-12 rounded-full bg-primary text-white flex items-center justify-center hover:scale-110 transition-transform shadow-lg shadow-primary/30"
              title={t("player.play", "Play")}
            >
              <IoPlay size={24} className="ml-1" />
            </button>

            <button
              onClick={() => setShowPlaylistModal(true)}
              className="w-10 h-10 rounded-full bg-white/10 backdrop-blur-md text-white flex items-center justify-center hover:bg-white/20 transition-colors"
              title={t("playlist.addButton", "Add to playlist")}
            >
              <IoAdd size={20} />
            </button>
          </div>

          {/* Match Score Badge */}
          {track.match > 0 && (
            <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur text-[10px] font-bold text-primary border border-white/5">
              {Math.round(track.match * 100)}% Match
            </div>
          )}
        </div>

        {/* Info */}
        <div className="p-4">
          <h3
            className="font-bold text-white truncate text-base leading-tight mb-1"
            title={track.name}
          >
            {track.name}
          </h3>
          <p className="text-sm text-zinc-400 truncate hover:text-primary transition-colors cursor-pointer">
            {track.artist}
          </p>
        </div>
      </div>

      {/* Playlist Modal - Note: We need a real track ID logic here.
          Recommendation returns metadata. Adding to playlist usually requires a Track ID in DB.
          We might need an intermediate step: "Import to Library" or "Search & Add".
          For now, let's assume we handle 'import on add' logic in parent or assume ID if available.
          Since Last.fm tracks don't have local IDs yet, this button might trigger a search/download flow.

          However, User asked to add to playlist.
          Let's fake the ID for visual completion or pass a special formatted ID "external:{artist}:{track}"
      */}
      <AddToPlaylistModal
        isOpen={showPlaylistModal}
        onClose={() => setShowPlaylistModal(false)}
        trackIds={[`external:${track.artist}:${track.name}`]}
      />
    </>
  );
};

export default RecommendationCard;
