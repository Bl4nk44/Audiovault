import TrackCard from "./TrackCard";
import ArtistCard from "./ArtistCard";
import PlaylistCard from "./PlaylistCard";
import { motion } from "framer-motion";
import { useState } from "react";
import { useTranslation } from "../../hooks/useTranslation";
import { v4 as uuidv4 } from "uuid";

import type { Track, Artist, Playlist } from "../../types";

type SearchResultItem = (Track | Artist | Playlist) & { type?: string };

interface SearchResultsProps {
  results: SearchResultItem[];
  isLoading: boolean;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

export default function SearchResults({ results, isLoading }: Readonly<SearchResultsProps>) {
  const { t } = useTranslation();

  const [skeletonIds] = useState(() => Array.from({ length: 10 }, () => uuidv4()));

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {skeletonIds.map((id) => (
          <div
            key={id}
            className="h-20 rounded-xl bg-white/5 animate-pulse border border-white/5"
          />
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-center py-20 text-muted-foreground"
      >
        <p className="text-lg">{t("search.noResults")}</p>
      </motion.div>
    );
  }

  // Type Guards
  const isArtist = (item: SearchResultItem): item is Artist => item.type === "artist";
  const isPlaylist = (item: SearchResultItem): item is Playlist => item.type === "playlist";
  const isTrack = (item: SearchResultItem): item is Track =>
    !item.type || item.type === "track" || item.type === "song";

  const artists = results.filter(isArtist);
  const playlists = results.filter(isPlaylist);
  const tracks = results.filter(isTrack);

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-8 pb-20">
      {tracks.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">{t("search.headers.tracks")}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {tracks.map((item) => (
              <TrackCard key={`${item.source}-${item.id}`} track={item} queue={tracks} />
            ))}
          </div>
        </section>
      )}

      {artists.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">{t("search.headers.artists")}</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {artists.map((item) => (
              <ArtistCard key={`${item.source}-${item.id}`} artist={item} />
            ))}
          </div>
        </section>
      )}

      {playlists.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">{t("search.headers.playlists")}</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {playlists.map((item) => (
              <PlaylistCard key={`${item.source}-${item.id}`} playlist={item} />
            ))}
          </div>
        </section>
      )}
    </motion.div>
  );
}
