import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { IoArrowForward, IoPerson } from "react-icons/io5";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import api from "../../services/api";
import type { RecommendedArtist } from "../../types/lastfm";

interface ArtistRecommendationCardProps {
  artist: RecommendedArtist;
}

const ArtistRecommendationCard: React.FC<ArtistRecommendationCardProps> = ({ artist }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  let badgeLabel: string | null = null;
  if (artist.match > 0) {
    badgeLabel = `${Math.round(artist.match * 100)}% Match`;
  } else if (artist.rank) {
    badgeLabel = `#${artist.rank}`;
  }

  const handleViewProfile = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/browse/search", {
        params: { q: artist.name, type: "artist", limit: 1 },
      });
      if (data && data.length > 0 && data[0].id) {
        navigate(`/artist/${data[0].id}`, { state: { source: data[0].source || "deezer" } });
      } else {
        toast.error(t("artist.not_found", "Nie znaleziono artysty w bibliotece"));
      }
    } catch {
      toast.error(t("common.error", "Wystąpił błąd"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="group relative bg-card/50 hover:bg-secondary transition-all duration-300 rounded-xl overflow-hidden border border-white/5 hover:border-primary/30">
      <div className="relative aspect-square w-full bg-secondary overflow-hidden">
        {artist.image_url ? (
          <img
            src={artist.image_url}
            alt={artist.name}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-secondary text-zinc-600">
            <IoPerson size={64} className="opacity-20" />
          </div>
        )}

        {/* Hover Overlay */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <button
            onClick={handleViewProfile}
            disabled={loading}
            className="px-4 py-2 bg-primary text-white rounded-full font-bold flex items-center gap-2 hover:scale-110 hover:opacity-80 transition-all shadow-lg shadow-primary/30 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {t("common.view_profile", "View Profile")}
            <IoArrowForward />
          </button>
        </div>

        {/* Match Score / Rank Badge */}
        {badgeLabel && (
          <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur text-[10px] font-bold text-primary border border-white/5">
            {badgeLabel}
          </div>
        )}
      </div>

      <div className="p-4 text-center">
        <a
          href={artist.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-bold text-white truncate text-lg mb-1 leading-tight group-hover:text-primary transition-colors block"
        >
          {artist.name}
        </a>
        <p className="text-xs text-zinc-500 uppercase tracking-widest font-bold">
          {t("common.artist", "Artist")}
        </p>
      </div>
    </div>
  );
};

export default ArtistRecommendationCard;
