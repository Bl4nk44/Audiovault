import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "../../lib/utils";
import type { Track } from "../../types";

interface TrackInfoProps {
  currentTrack: Track;
  isExpanded: boolean;
}

export function TrackInfo({ currentTrack, isExpanded }: Readonly<TrackInfoProps>) {
  const navigate = useNavigate();
  const [imgError, setImgError] = useState(false);

  return (
    <div
      className={cn(
        "flex items-center gap-3 md:gap-4 transition-all overflow-hidden",
        isExpanded ? "flex-col text-center mb-8 w-full" : "flex-1 w-0 min-w-0 md:w-1/3 md:min-w-0"
      )}
    >
      <div
        className={cn(
          "relative overflow-hidden rounded-xl shadow-2xl shrink-0",
          isExpanded ? "w-64 h-64 md:w-80 md:h-80 mb-6 aspect-square" : "w-10 h-10 md:w-14 md:h-14"
        )}
      >
        {currentTrack.cover && !imgError ? (
          <img
            key={currentTrack.id}
            src={currentTrack.cover}
            alt={currentTrack.title}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full bg-linear-to-br from-gray-800 to-gray-900 flex items-center justify-center">
            <span className="text-2xl">🎵</span>
          </div>
        )}
      </div>
      <div className={cn("min-w-0", isExpanded ? "w-full" : "flex-1")}>
        <h3
          className={cn(
            "font-bold text-white truncate",
            isExpanded ? "text-3xl" : "text-sm md:text-base"
          )}
        >
          {currentTrack.title}
        </h3>
        {currentTrack.artist_id || currentTrack.spotify_artist_id ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              const id = currentTrack.artist_id || currentTrack.spotify_artist_id;
              navigate(`/artist/${id}`);
              // Close player expand if open? Maybe handled by layout.
            }}
            className={cn(
              "text-gray-400 truncate hover:text-primary hover:underline transition-colors block text-left",
              isExpanded ? "text-xl" : "text-xs"
            )}
          >
            {currentTrack.artist}
          </button>
        ) : (
          <p className={cn("text-gray-400 truncate", isExpanded ? "text-xl" : "text-xs")}>
            {currentTrack.artist}
          </p>
        )}
      </div>
    </div>
  );
}
