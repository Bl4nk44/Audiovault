import React from "react";
import { useTranslation } from "react-i18next";
import { IoArrowForward, IoPerson } from "react-icons/io5";
import type { RecommendedArtist } from "../../types/lastfm";

interface ArtistRecommendationCardProps {
  artist: RecommendedArtist;
}

const ArtistRecommendationCard: React.FC<ArtistRecommendationCardProps> = ({ artist }) => {
  const { t } = useTranslation();

  return (
    <div className="group relative bg-zinc-900/50 hover:bg-zinc-800 transition-all duration-300 rounded-xl overflow-hidden border border-white/5 hover:border-primary/30">
      <div className="relative aspect-square w-full bg-zinc-800 overflow-hidden">
        {artist.image_url ? (
          <img
            src={artist.image_url}
            alt={artist.name}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-zinc-800 text-zinc-600">
            <IoPerson size={64} className="opacity-20" />
          </div>
        )}

        {/* Hover Overlay */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <a
            href={artist.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-primary text-white rounded-full font-bold flex items-center gap-2 hover:scale-110 hover:opacity-80 transition-all shadow-lg shadow-primary/30"
          >
            {t("common.view_profile", "View Profile")}
            <IoArrowForward />
          </a>
        </div>

        {/* Match Score Badge */}
        {artist.match > 0 && (
          <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur text-[10px] font-bold text-primary border border-white/5">
            {Math.round(artist.match * 100)}% Match
          </div>
        )}
      </div>

      <div className="p-4 text-center">
        <h3 className="font-bold text-white truncate text-lg mb-1 leading-tight group-hover:text-primary transition-colors">
          {artist.name}
        </h3>
        <p className="text-xs text-zinc-500 uppercase tracking-widest font-bold">
          {t("common.artist", "Artist")}
        </p>
      </div>
    </div>
  );
};

export default ArtistRecommendationCard;
