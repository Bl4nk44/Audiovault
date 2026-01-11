import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Music,
  Disc,
  Loader2,
  Plus,
  Check,
  PlayCircle,
} from "lucide-react";
import { artistsApi } from "../api/artists";
import Button from "../components/ui/Button";
import { useStore } from "../store/useStore";
import { notify as toast } from "../utils/notify";
import TrackCard from "../components/search/TrackCard";
import { isValidImageUrl } from "../utils/validation";

export default function ArtistProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  // Safe cast or default to 'local' if no state provided, but we know searching gives 'spotify'
  const source = location.state?.source || "local";

  const { watchlist, addToWatchlist, removeFromWatchlist } = useStore();

  const {
    data: artist,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["artist", id, source],
    queryFn: () => artistsApi.getById(id!, source),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !artist) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <p className="text-red-400">Failed to load artist profile</p>
        <Button onClick={() => navigate(-1)} variant="outline">
          Go Back
        </Button>
      </div>
    );
  }

  const rawHeroImage =
    artist.image_url ||
    artist.images?.banner ||
    artist.images?.image_url ||
    artist.images?.url;

  // Validated by isValidImageUrl to prevent XSS (javascript: etc.)
  const heroImage = isValidImageUrl(rawHeroImage) ? rawHeroImage : null;

  const isWatched = watchlist.some(
    (item) =>
      item.source_id === artist.spotify_id ||
      item.source_id === artist.deezer_id ||
      item.source_id === artist.id
  );
  const watchedItem = watchlist.find(
    (item) =>
      item.source_id === artist.spotify_id ||
      item.source_id === artist.deezer_id ||
      item.source_id === artist.id
  );

  const handleWatchlistToggle = () => {
    if (isWatched && watchedItem) {
      removeFromWatchlist(watchedItem.id);
      toast.success("Removed from watchlist");
    } else {
      addToWatchlist({
        source: "spotify", // Default or detect
        source_id: artist.spotify_id || artist.id,
        source_name: artist.name,
        watch_type: "artist",
        auto_download: false,
        new_items_count: 0,
        metadata_content: { image_url: heroImage || undefined },
      });
      toast.success("Added to watchlist");
    }
  };

  return (
    <div className="space-y-8 pb-10">
      {/* Hero Section */}
      <div className="relative h-64 md:h-80 rounded-3xl overflow-hidden group">
        {heroImage ? (
          // deepcode ignore DomXss: Source is validated by strict protocol check
          <img
            src={heroImage}
            alt={artist.name}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full bg-linear-to-br from-gray-800 to-gray-900 flex items-center justify-center">
            <Music className="w-24 h-24 text-gray-700" />
          </div>
        )}
        {/* ... (Overlay content remains same) ... */}
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
            {artist.name}
          </motion.h1>
          {artist.bio && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="text-gray-300 max-w-2xl line-clamp-2"
            >
              {artist.bio}
            </motion.p>
          )}
        </div>
      </div>

      {/* Tracks Section */}
      {artist.tracks && artist.tracks.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <PlayCircle className="w-6 h-6 text-primary" />
            Popular Tracks
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {artist.tracks.map((track) => (
              <TrackCard
                key={track.id}
                track={{
                  ...track,
                  source: "spotify",
                  duration_ms: track.duration_ms,
                  cover: track.image_url || artist.image_url, // Use image_url from track or fallback to artist
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Albums Section */}
      {artist.albums && artist.albums.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Disc className="w-6 h-6 text-primary" />
            Albums
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {artist.albums.map((album) => {
              // @ts-expect-error - Backend returns simple image_url, type definition has images Record
              const albumCover = album.image_url || album.images?.url;

              const isValid = isValidImageUrl(albumCover);

              return (
                <div
                  key={album.id}
                  className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors group cursor-pointer"
                >
                  <div className="aspect-square bg-black/40 rounded-lg mb-3 overflow-hidden">
                    {isValid ? (
                      // deepcode ignore DomXss: Source is validated by strict protocol check
                      <img
                        src={albumCover}
                        alt={album.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Disc className="w-10 h-10 text-gray-600" />
                      </div>
                    )}
                  </div>
                  <h3 className="font-semibold truncate text-white">
                    {album.title}
                  </h3>
                  <p className="text-sm text-gray-400">
                    {album.release_date
                      ? new Date(album.release_date).getFullYear()
                      : "Unknown"}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
