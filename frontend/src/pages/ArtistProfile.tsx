import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, Check, Disc, Loader2, Music, PlayCircle, Plus } from "lucide-react";
import { useState } from "react";
import { IoDownloadOutline } from "react-icons/io5";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { artistsApi } from "../api/artists";
import TrackCard from "../components/search/TrackCard";
import Button from "../components/ui/Button";
import api from "../services/api";
import { useStore } from "../store/useStore";
import type { Album } from "../types";
import { notify as toast } from "../utils/notify";
import { isValidImageUrl } from "../utils/validation";

export default function ArtistProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  // Safe cast or default to 'local' if no state provided, but we know searching gives 'spotify'
  const source = location.state?.source || "local";

  const { watchlist, addToWatchlist, removeFromWatchlist } = useStore();
  const [isDownloading, setIsDownloading] = useState(false);

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
    artist.image_url || artist.images?.banner || artist.images?.image_url || artist.images?.url;

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

  const handleToggleWatchlist = async () => {
    if (isWatched && watchedItem) {
      removeFromWatchlist(watchedItem.id);
      toast.success("Removed from watchlist");
      return;
    }

    addToWatchlist({
      source: "spotify",
      source_id: artist.spotify_id || artist.id,
      source_name: artist.name,
      watch_type: "artist",
      auto_download: false, // Default to FALSE for just "Follow"
      new_items_count: 0,
      metadata_content: { image_url: heroImage || undefined },
    });
    toast.success("Following " + artist.name);
  };

  const handleDownloadDiscography = async () => {
    // Logic for mass download
    if (!isWatched) {
      await handleToggleWatchlist();
    }

    setIsDownloading(true);
    try {
      const response = await api.post(
        `/downloads/artist/${artist.spotify_id || artist.id}/download-all`,
        { source: "spotify" }
      );

      toast.success(`Queued ${response.data.queued_count} tracks for download`);
    } catch (error) {
      console.error("Failed to download all:", error);
      toast.error("Failed to queue downloads");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDownloadAlbum = async (album: Album) => {
    try {
      // Use spotify_id if available (for search results), otherwise id (for local/database items)
      // If we are in "spotify" source mode (which search usually is), we should prefer spotify_id or id if that's what semantic is.
      // Actually backend expects an ID it can use to find the album.
      // If we are browsing Spotify artist, we probably have spotify IDs.
      const targetId = album.spotify_id || album.id;

      const response = await api.post(`/downloads/album/${targetId}/download`, {
        source: "spotify",
      });

      toast.success(response.data.message || "Album queued for download");
    } catch (error: any) {
      console.error("Failed to download album:", error);
      toast.error(error.response?.data?.detail || "Failed to queue album download");
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
        {/* Helper gradient for text readability */}
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
            <Button
              variant={isWatched ? "secondary" : "secondary"} // Keep secondary if watched to show state
              onClick={handleToggleWatchlist}
              className="gap-2 bg-black/50 hover:bg-black/70 border border-white/10"
            >
              {isWatched ? <Check size={16} /> : <Plus size={16} />}
              {isWatched ? "Following" : "Follow"}
            </Button>

            <Button
              variant="primary"
              onClick={handleDownloadDiscography}
              disabled={isDownloading}
              className="gap-2"
            >
              {isDownloading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Downloading...
                </>
              ) : (
                <>
                  <IoDownloadOutline size={16} />
                  Download Discography
                </>
              )}
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
      {(() => {
        const albums =
          artist.albums?.filter(
            (a: Album) => a.album_type === "album" || (!a.album_type && (a.total_tracks ?? 0) > 3)
          ) || [];

        return (
          albums.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <Disc className="w-6 h-6 text-primary" />
                Albums
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {albums.map((album: Album) => {
                  const albumCover = album.image_url || album.images?.url;
                  const isValid = isValidImageUrl(albumCover);

                  return (
                    <div key={album.id} className="group relative">
                      <div
                        role="button"
                        tabIndex={0}
                        onClick={() =>
                          navigate(`/album/${album.id}`, { state: { source: "spotify" } })
                        }
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            navigate(`/album/${album.id}`, { state: { source: "spotify" } });
                          }
                        }}
                        className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors cursor-pointer w-full text-left"
                      >
                        <div className="aspect-square bg-black/40 rounded-lg mb-3 overflow-hidden relative group/image">
                          {isValid ? (
                            <img
                              src={albumCover}
                              alt={album.title}
                              className="w-full h-full object-cover group-hover/image:scale-105 transition-transform"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Disc className="w-10 h-10 text-gray-600" />
                            </div>
                          )}

                          {/* Download Overlay */}
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover/image:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <Button
                              variant="primary"
                              size="icon"
                              className="rounded-full w-10 h-10 transform scale-90 hover:scale-100 transition-transform"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadAlbum(album);
                              }}
                              title="Download Album"
                            >
                              <IoDownloadOutline size={20} />
                            </Button>
                          </div>
                        </div>
                        <h3 className="font-semibold truncate text-white">{album.title}</h3>
                        <p className="text-sm text-gray-400">
                          {album.release_date
                            ? new Date(album.release_date).getFullYear()
                            : "Unknown"}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )
        );
      })()}

      {/* Singles & EPs Section */}
      {(() => {
        const singles =
          artist.albums?.filter(
            (a: Album) => a.album_type === "single" || a.album_type === "compilation"
          ) || [];

        return (
          singles.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <Music className="w-6 h-6 text-primary" />
                Singles & EPs
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {singles.map((single: Album) => {
                  const singleCover = single.image_url || single.images?.url;
                  const isValid = isValidImageUrl(singleCover);

                  return (
                    <div key={single.id} className="group relative">
                      <div
                        role="button"
                        tabIndex={0}
                        onClick={() =>
                          navigate(`/album/${single.id}`, { state: { source: "spotify" } })
                        }
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            navigate(`/album/${single.id}`, { state: { source: "spotify" } });
                          }
                        }}
                        className="bg-white/5 rounded-xl p-3 hover:bg-white/10 transition-colors cursor-pointer w-full text-left"
                      >
                        <div className="aspect-square bg-black/40 rounded-lg mb-2 overflow-hidden relative group/image">
                          {isValid ? (
                            <img
                              src={singleCover}
                              alt={single.title}
                              className="w-full h-full object-cover group-hover/image:scale-105 transition-transform"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Music className="w-8 h-8 text-gray-600" />
                            </div>
                          )}

                          {/* Download Overlay */}
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover/image:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <Button
                              variant="primary"
                              size="icon"
                              className="rounded-full w-10 h-10 transform scale-90 hover:scale-100 transition-transform"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadAlbum(single);
                              }}
                              title="Download Single/EP"
                            >
                              <IoDownloadOutline size={20} />
                            </Button>
                          </div>
                        </div>
                        <h3 className="font-medium text-sm truncate text-white">{single.title}</h3>
                        <p className="text-xs text-gray-400">
                          {single.release_date ? new Date(single.release_date).getFullYear() : ""}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )
        );
      })()}
    </div>
  );
}
