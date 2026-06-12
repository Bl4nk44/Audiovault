import React from "react";
import { useTranslation } from "react-i18next";
import { IoList, IoPlay } from "react-icons/io5";
import { useNavigate } from "react-router-dom";
import type { RecommendedPlaylist } from "../../types/lastfm";

interface PlaylistRecommendationCardProps {
  playlist: RecommendedPlaylist;
}

const PlaylistRecommendationCard: React.FC<PlaylistRecommendationCardProps> = ({ playlist }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleEnterPlaylist = (e: React.MouseEvent) => {
    // Prevent navigating to Spotify link if we click the card
    e.preventDefault();
    e.stopPropagation();
    navigate(`/playlist/${playlist.id}`, { state: { source: playlist.source } });
  };

  return (
    <button
      onClick={handleEnterPlaylist}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ")
          handleEnterPlaylist(e as unknown as React.MouseEvent);
      }}
      className="text-left w-full cursor-pointer group relative bg-card/50 hover:bg-secondary transition-all duration-300 rounded-xl overflow-hidden border border-white/5 hover:border-primary/30 focus:outline-none focus:ring-2 focus:ring-primary"
    >
      <div className="relative aspect-square w-full bg-secondary overflow-hidden">
        {playlist.image_url ? (
          <img
            src={playlist.image_url}
            alt={playlist.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-secondary text-zinc-600">
            <IoList size={64} className="opacity-20" />
          </div>
        )}

        {/* Hover Overlay */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <a
            href={playlist.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="w-14 h-14 rounded-full bg-primary text-white flex items-center justify-center hover:scale-110 hover:opacity-80 transition-all shadow-lg shadow-primary/30"
          >
            <IoPlay size={32} className="ml-1" />
          </a>
        </div>
      </div>

      <div className="p-4">
        <h3 className="font-bold text-white truncate text-base leading-tight mb-1 group-hover:text-primary transition-colors">
          {playlist.title}
        </h3>
        <p className="text-sm text-zinc-400">
          {playlist.track_count} {t("common.tracks", "tracks")}
        </p>
      </div>
    </button>
  );
};

export default PlaylistRecommendationCard;
