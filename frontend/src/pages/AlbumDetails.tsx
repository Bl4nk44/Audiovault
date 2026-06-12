import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, Calendar, Clock, Disc, Download, ListPlus, Loader2, Play } from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { albumsApi } from "../api/albums";
import AddToPlaylistModal from "../components/AddToPlaylistModal";
import TrackCard from "../components/search/TrackCard";
import Button from "../components/ui/Button";
import { useStore } from "../store/useStore";
import { notify as toast } from "../utils/notify";
import { isValidImageUrl } from "../utils/validation";

export default function AlbumDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const source = location.state?.source || "deezer";

  const { addToQueue } = useStore();
  const [showPlaylistModal, setShowPlaylistModal] = useState(false);

  const {
    data: album,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["album", id, source],
    queryFn: () => albumsApi.getById(id!, source),
    enabled: !!id,
  });

  const handleDownloadAll = () => {
    if (!album?.tracks) return;

    album.tracks.forEach((track) => {
      addToQueue({
        id: track.id,
        title: track.title,
        artist: track.artist,
        cover: track.image_url || album.image_url || undefined,
        duration_ms: track.duration_ms,
        source: track.source,
      });
    });

    toast.success(`Added ${album.tracks.length} tracks to download queue`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !album) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <p className="text-red-400">Failed to load album</p>
        <Button onClick={() => navigate(-1)} variant="outline">
          Go Back
        </Button>
      </div>
    );
  }

  const albumCover = isValidImageUrl(album.image_url) ? album.image_url : null;
  const releaseYear = album.release_date ? new Date(album.release_date).getFullYear() : null;

  const totalDuration = album.tracks?.reduce((acc, track) => acc + (track.duration_ms || 0), 0);
  const formatDuration = (ms: number) => {
    const minutes = Math.floor(ms / 60000);
    return `${minutes} min`;
  };

  return (
    <div className="space-y-8 pb-10">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row gap-8">
        {/* Album Cover */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full md:w-64 lg:w-80 aspect-square rounded-2xl overflow-hidden shadow-2xl shrink-0"
        >
          {albumCover ? (
            <img src={albumCover} alt={album.title} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-secondary flex items-center justify-center">
              <Disc className="w-24 h-24 text-gray-600" />
            </div>
          )}
        </motion.div>

        {/* Album Info */}
        <div className="flex flex-col justify-end space-y-4">
          <Button
            variant="ghost"
            size="sm"
            className="self-start text-gray-400 hover:text-white -ml-2"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>

          <div className="space-y-2">
            <span className="text-sm font-medium text-primary uppercase tracking-wider">
              {album.album_type === "single" ? "Single" : album.album_type === "compilation" ? "Compilation" : "Album" /* eslint-disable-line sonarjs/no-nested-conditional */}
            </span>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-4xl md:text-5xl font-bold text-white"
            >
              {album.title}
            </motion.h1>
            <button
              type="button"
              className="text-xl text-gray-300 cursor-pointer hover:text-primary transition-colors bg-transparent border-none text-left"
              onClick={() =>
                navigate(`/artist/${album.artist_id}`, {
                  state: { source },
                })
              }
            >
              {album.artist}
            </button>
          </div>

          <div className="flex items-center gap-4 text-sm text-gray-400">
            {releaseYear && (
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {releaseYear}
              </span>
            )}
            <span>{album.total_tracks} tracks</span>
            {totalDuration > 0 && (
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {formatDuration(totalDuration)}
              </span>
            )}
            {album.label && <span>• {album.label}</span>}
          </div>

          <div className="flex items-center gap-3 pt-4">
            <Button variant="primary" size="lg" onClick={handleDownloadAll} className="gap-2">
              <Download className="w-5 h-5" />
              Download Album
            </Button>

            <Button
              variant="secondary"
              size="lg"
              onClick={() => setShowPlaylistModal(true)}
              className="gap-2"
            >
              <ListPlus className="w-5 h-5" />
              Add to Playlist
            </Button>
          </div>
        </div>
      </div>

      <AddToPlaylistModal
        isOpen={showPlaylistModal}
        onClose={() => setShowPlaylistModal(false)}
        trackIds={album.tracks?.map((t) => t.id || t.deezer_id || t.spotify_id || "").filter(Boolean) || []}
      />

      {/* Tracks Section */}
      {album.tracks && album.tracks.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Play className="w-6 h-6 text-primary" />
            Tracks
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {album.tracks.map((track) => (
              <TrackCard
                key={track.id}
                track={{
                  ...track,
                  image_url: track.image_url || undefined,
                  cover: track.image_url || album.image_url || undefined,
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
