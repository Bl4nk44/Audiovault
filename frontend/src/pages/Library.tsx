import { AnimatePresence, motion } from "framer-motion";
import { Edit2, Folder, LayoutGrid, List, ListPlus, Music, Play, RefreshCw, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { FaMusic } from "react-icons/fa";
import { SiApplemusic, SiSpotify, SiTidal, SiYoutube } from "react-icons/si";
import { useNavigate, useSearchParams } from "react-router-dom";
import AddToPlaylistModal from "../components/AddToPlaylistModal";
import ConfirmModal from "../components/ui/ConfirmModal";
import { useTranslation } from "../hooks/useTranslation";
import api from "../services/api";
import { useStore } from "../store/useStore";
import { notify as toast } from "../utils/notify";

interface LibraryItem {
  id: string;
  track_id: string;
  status: string;
  file_path: string;
  created_at: string;
  source?: string;
  playlist_name?: string;
  track: {
    title: string;
    artist: string;
    album?: string;
    image_url?: string;
    filename?: string;
    artist_id?: string;
    spotify_artist_id?: string;
  };
}

interface FolderStructure {
  [source: string]: string[];
}

type ViewMode = "root" | "service" | "playlist";

const SourceIcon = ({ source, size = 24 }: { source: string; size?: number }) => {
  switch (source?.toLowerCase()) {
    case "spotify":
      return <SiSpotify size={size} className="text-[#1DB954]" />;
    case "youtube":
      return <SiYoutube size={size} className="text-[#FF0000]" />;
    case "apple_music":
      return <SiApplemusic size={size} className="text-[#FA243C]" />;
    case "tidal":
      return <SiTidal size={size} className="text-white" />;
    case "soundcloud":
      return (
        <div className="text-[#FF5500] font-bold text-xs" style={{ fontSize: size }}>
          SC
        </div>
      );
    case "deezer":
      return (
        <div className="text-white font-bold text-xs" style={{ fontSize: size }}>
          DZ
        </div>
      );
    case "amazon_music":
      return (
        <div className="text-[#00A8E1] font-bold text-xs" style={{ fontSize: size }}>
          AM
        </div>
      );
    default:
      return <FaMusic size={size} className="text-gray-400" />;
  }
};

interface RootViewProps {
  folders: FolderStructure;
  onServiceClick: (source: string) => void;
  displayMode: "grid" | "list";
}

const RootView = ({ folders, onServiceClick, displayMode }: RootViewProps) => {
  const { t } = useTranslation();

  if (displayMode === "list") {
    return (
      <div className="space-y-2">
        {Object.keys(folders).map((source) => (
          <motion.button
            key={source}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            whileHover={{ x: 4 }}
            onClick={() => onServiceClick(source)}
            className="w-full bg-card/40 border border-border rounded-xl px-5 py-4 cursor-pointer hover:bg-card/60 transition-colors flex items-center gap-4 text-left"
          >
            <div className="p-3 bg-secondary/50 rounded-full shrink-0">
              <SourceIcon source={source} size={28} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-bold text-foreground capitalize">{source}</h3>
              <p className="text-sm text-muted-foreground">
                {folders[source].length} {t("filters.playlists")}
              </p>
            </div>
          </motion.button>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {Object.keys(folders).map((source) => (
        <motion.button
          key={source}
          initial="rest"
          whileHover="hover"
          whileTap="tap"
          onClick={() => onServiceClick(source)}
          className="bg-card/40 border border-border rounded-2xl p-6 cursor-pointer hover:bg-card/60 transition-colors flex flex-col items-center justify-center gap-6 text-center aspect-square group w-full"
        >
          <motion.div
            variants={{
              rest: { scale: 1, rotate: 0 },
              hover: {
                scale: 1.2,
                rotate: 5,
                transition: { type: "spring", stiffness: 300 },
              },
              tap: { scale: 0.9 },
            }}
            className="p-6 bg-secondary/50 rounded-full"
          >
            <SourceIcon source={source} size={72} />
          </motion.div>
          <div>
            <motion.h3
              variants={{
                rest: { y: 0 },
                hover: { y: -2 },
              }}
              className="text-2xl font-bold text-foreground capitalize mb-1"
            >
              {source}
            </motion.h3>
            <p className="text-sm text-muted-foreground">
              {folders[source].length} {t("filters.playlists")}
            </p>
          </div>
        </motion.button>
      ))}
    </div>
  );
};

interface ServiceViewProps {
  playlists: string[];
  onAllTracksClick: () => void;
  onPlaylistClick: (playlist: string) => void;
  onPlaylistDelete: (e: React.MouseEvent, playlist: string) => void;
  displayMode: "grid" | "list";
}

const ServiceView = ({
  playlists,
  onAllTracksClick,
  onPlaylistClick,
  onPlaylistDelete,
  displayMode,
}: ServiceViewProps) => {
  const { t } = useTranslation();

  if (displayMode === "list") {
    return (
      <div className="space-y-2">
        {/* All Tracks Row */}
        <motion.button
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          whileHover={{ x: 4 }}
          onClick={onAllTracksClick}
          className="w-full bg-primary/20 border border-primary/30 rounded-xl px-5 py-4 cursor-pointer hover:bg-primary/30 transition-colors flex items-center gap-4 text-left"
        >
          <div className="p-3 bg-black/20 rounded-full shrink-0">
            <Music size={28} className="text-white" />
          </div>
          <h3 className="text-lg font-bold text-white">{t("library.allTracks")}</h3>
        </motion.button>

        {/* Playlist Rows */}
        {playlists.map((playlist) => (
          <motion.div
            key={playlist || "uncategorized"}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            whileHover={{ x: 4 }}
            onClick={() => onPlaylistClick(playlist || "__none__")}
            className="w-full bg-card/40 border border-border rounded-xl px-5 py-4 cursor-pointer hover:bg-card/60 transition-colors flex items-center gap-4 relative group"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                onPlaylistClick(playlist || "__none__");
              }
            }}
          >
            <div className="p-3 bg-secondary/50 rounded-full shrink-0">
              <Folder size={28} className="text-blue-400" />
            </div>
            <h3 className="flex-1 text-lg font-bold text-foreground truncate">
              {playlist || t("library.uncategorized")}
            </h3>
            {playlist && playlist !== "__none__" && (
              <button
                onClick={(e) => onPlaylistDelete(e, playlist)}
                className="p-2 bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white rounded-full opacity-0 group-hover:opacity-100 transition-all duration-200 shrink-0"
                title="Delete playlist"
              >
                <Trash2 size={16} />
              </button>
            )}
          </motion.div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {/* All Tracks Card */}
      <motion.button
        initial="rest"
        whileHover="hover"
        whileTap="tap"
        onClick={onAllTracksClick}
        className="bg-primary/20 border border-primary/30 rounded-2xl p-6 cursor-pointer hover:bg-primary/30 transition-colors flex flex-col items-center justify-center gap-6 text-center aspect-square w-full"
      >
        <motion.div
          variants={{
            rest: { scale: 1 },
            hover: {
              scale: 1.15,
              transition: { type: "spring", stiffness: 400 },
            },
            tap: { scale: 0.95 },
          }}
          className="p-5 bg-black/20 rounded-full"
        >
          <Music size={56} className="text-white" />
        </motion.div>
        <h3 className="text-xl font-bold text-white">{t("library.allTracks")}</h3>
      </motion.button>

      {/* Playlist Cards */}
      {playlists.map((playlist) => (
        <motion.div
          key={playlist || "uncategorized"}
          initial="rest"
          whileHover="hover"
          whileTap="tap"
          onClick={() => onPlaylistClick(playlist || "__none__")}
          className="bg-card/40 border border-border rounded-2xl p-6 cursor-pointer hover:bg-card/60 transition-colors flex flex-col items-center justify-center gap-6 text-center aspect-square relative group w-full"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              onPlaylistClick(playlist || "__none__");
            }
          }}
        >
          <motion.div
            variants={{
              rest: { scale: 1, rotate: 0 },
              hover: { scale: 1.1, rotate: -3 },
              tap: { scale: 0.95 },
            }}
            className="p-5 bg-secondary/50 rounded-full"
          >
            <Folder size={56} className="text-blue-400" />
          </motion.div>
          <div>
            <h3 className="text-xl font-bold text-foreground line-clamp-2">
              {playlist || t("library.uncategorized")}
            </h3>
          </div>

          {/* Delete Playlist Button */}
          {playlist && playlist !== "__none__" && (
            <button
              onClick={(e) => onPlaylistDelete(e, playlist)}
              className="absolute top-3 right-3 p-2 bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white rounded-full opacity-0 group-hover:opacity-100 transition-all duration-200"
              title="Delete playlist"
            >
              <Trash2 size={16} />
            </button>
          )}
        </motion.div>
      ))}
    </div>
  );
};

interface LibraryBreadcrumbsProps {
  viewMode: ViewMode;
  selectedService: string | null;
  selectedPlaylist: string | null;
  onRootClick: () => void;
  onServiceClick: () => void;
}

const LibraryBreadcrumbs = ({
  viewMode,
  selectedService,
  selectedPlaylist,
  onRootClick,
  onServiceClick,
}: LibraryBreadcrumbsProps) => {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
      <button
        onClick={onRootClick}
        className={`hover:text-foreground transition-colors ${
          viewMode === "root" ? "text-foreground font-bold" : ""
        }`}
      >
        {t("sidebar.library")}
      </button>
      {selectedService && (
        <>
          <span>/</span>
          <button
            onClick={onServiceClick}
            className={`hover:text-foreground transition-colors ${
              viewMode === "service" ? "text-foreground font-bold" : ""
            }`}
          >
            {selectedService.charAt(0).toUpperCase() + selectedService.slice(1)}
          </button>
        </>
      )}
      {selectedPlaylist && (
        <>
          <span>/</span>
          <span className="text-foreground font-bold">
            {selectedPlaylist === "__none__" ? t("library.uncategorized") : selectedPlaylist}
          </span>
        </>
      )}
    </div>
  );
};

interface PlaylistViewProps {
  items: LibraryItem[];
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  selectedPlaylist: string | null;
  selectedService: string | null;
  loading: boolean;
  total: number;
  limit: number;
  page: number;
  setPage: (p: number | ((prev: number) => number)) => void;
  onEdit: (item: LibraryItem) => void;
  onDelete: (id: string) => void;
  onAddToPlaylist: (trackId: string) => void;
  displayMode: "grid" | "list";
}

const PlaylistView = ({
  items,
  searchQuery,
  setSearchQuery,
  selectedPlaylist,
  selectedService,
  loading,
  total,
  limit,
  page,
  setPage,
  onEdit,
  onDelete,
  onAddToPlaylist,
  displayMode,
}: PlaylistViewProps) => {
  const { t } = useTranslation();
  const { currentTrack, isPlaying, playTrack, togglePlay } = useStore();
  const navigate = useNavigate();

  const filteredItems = items.filter(
    (item) =>
      item.track.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.track.artist.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const totalPages = Math.ceil(total / limit);

  let headerTitle = `${t("library.allTracks")} ${selectedService || ""}`;
  if (selectedPlaylist) {
    headerTitle = selectedPlaylist === "__none__" ? t("library.uncategorized") : selectedPlaylist;
  }

  const buildQueue = (source: LibraryItem[]) =>
    source.map((i) => ({
      id: i.track_id,
      title: i.track.title,
      artist: i.track.artist,
      cover: i.track.image_url,
      source: "local" as const,
      album: i.track.album,
      filename: i.track.filename,
    }));

  return (
    <>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">{headerTitle}</h2>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search tracks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-full py-2 pl-10 pr-4 text-white focus:outline-none focus:border-primary/50 transition-colors"
          />
        </div>
      </div>

      {loading && <div className="text-center py-20 text-gray-500">Loading tracks...</div>}

      {!loading && filteredItems.length === 0 && (
        <div className="text-center py-20 text-gray-500">No tracks found.</div>
      )}

      {!loading && filteredItems.length > 0 && (
        <>
          {displayMode === "grid" ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              <AnimatePresence>
                {filteredItems.map((item) => {
                  const isCurrent = currentTrack?.id === item.track_id;
                  const isPlayingCurrent = isCurrent && isPlaying;
                  return (
                    <motion.div
                      key={item.id}
                      layout
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className={`group bg-card/40 border rounded-xl overflow-hidden cursor-pointer transition-colors ${
                        isCurrent ? "border-primary/60 bg-primary/10" : "border-border hover:bg-card/60"
                      }`}
                    >
                      <button
                        className="w-full aspect-square relative border-0 p-0 m-0"
                        onClick={() => {
                          if (isCurrent && isPlaying) {
                            togglePlay();
                          } else {
                            playTrack(
                              {
                                id: item.track_id,
                                title: item.track.title,
                                artist: item.track.artist,
                                cover: item.track.image_url,
                                source: "local",
                                album: item.track.album,
                                filename: item.track.filename,
                              },
                              buildQueue(filteredItems)
                            );
                          }
                        }}
                      >
                        {item.track.image_url ? (
                          <img
                            src={item.track.image_url}
                            alt={item.track.title}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full bg-secondary flex items-center justify-center">
                            <Music size={32} className="text-gray-600" />
                          </div>
                        )}
                        {isPlayingCurrent ? (
                          <div className="absolute inset-0 bg-black/60 flex items-center justify-center gap-0.5">
                            {[1, 2, 3].map((i) => (
                              <motion.div
                                key={i}
                                animate={{ height: [3, 14, 3] }}
                                transition={{
                                  duration: 0.5,
                                  repeat: Infinity,
                                  repeatType: "reverse",
                                  delay: i * 0.1,
                                  ease: "easeInOut",
                                }}
                                className="w-1 bg-primary rounded-full"
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <Play size={28} className="fill-white text-white" />
                          </div>
                        )}
                      </button>
                      <div className="p-3">
                        <p className={`text-sm font-medium truncate ${isCurrent ? "text-primary" : "text-white"}`}>
                          {item.track.title}
                        </p>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            const id = item.track.artist_id || item.track.spotify_artist_id;
                            if (id) navigate(`/artist/${id}`);
                            else navigate(`/search?q=${encodeURIComponent(item.track.artist)}&type=artist`);
                          }}
                          className="text-xs text-gray-400 hover:text-primary hover:underline transition-colors truncate w-full text-left block"
                        >
                          {item.track.artist}
                        </button>
                      </div>
                      <div className="px-3 pb-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => onAddToPlaylist(item.track_id)}
                          className="p-1.5 text-gray-400 hover:text-primary hover:bg-primary/10 rounded-full transition-colors"
                          title="Add to Playlist"
                        >
                          <ListPlus size={14} />
                        </button>
                        <button
                          onClick={() => onEdit(item)}
                          className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                          title="Edit Info"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => onDelete(item.id)}
                          className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-full transition-colors"
                          title="Delete File"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          ) : (
          <div className="bg-black/20 border border-white/5 rounded-2xl overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-white/5 text-gray-400 text-sm uppercase font-medium hidden md:table-header-group">
                <tr>
                  <th className="px-4 md:px-6 py-4">Track</th>
                  <th className="px-4 md:px-6 py-4">Artist</th>
                  <th className="px-4 md:px-6 py-4 hidden lg:table-cell">Album</th>
                  <th className="px-4 md:px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                <AnimatePresence>
                  {filteredItems.map((item) => {
                    const isCurrent = currentTrack?.id === item.track_id;
                    const isPlayingCurrent = isCurrent && isPlaying;

                    return (
                      <motion.tr
                        key={item.id}
                        layout
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className={`
                            group transition-colors relative border-b border-white/5 cursor-pointer
                            ${
                              isPlayingCurrent
                                ? "bg-primary/10 border-l-4 border-l-primary"
                                : "hover:bg-white/5 border-l-4 border-l-transparent"
                            }
                          `}
                      >
                        <td className="px-3 md:px-6 py-3 md:py-4">
                          <div className="flex items-center gap-3 md:gap-4 min-w-0">
                            <button
                              className={`relative w-10 h-10 md:w-10 md:h-10 rounded overflow-hidden cursor-pointer group/img shrink-0 border-0 p-0 m-0 ${
                                isCurrent ? "shadow-[0_0_10px_rgba(var(--primary-rgb),0.5)]" : ""
                              }`}
                              onClick={() => {
                                if (currentTrack?.id === item.track_id && isPlaying) {
                                  togglePlay();
                                } else {
                                  playTrack(
                                    {
                                      id: item.track_id,
                                      title: item.track.title,
                                      artist: item.track.artist,
                                      cover: item.track.image_url,
                                      source: "local",
                                      album: item.track.album,
                                      filename: item.track.filename,
                                    },
                                    buildQueue(filteredItems)
                                  );
                                }
                              }}
                            >
                              {item.track.image_url ? (
                                <img
                                  src={item.track.image_url}
                                  alt={item.track.title}
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <div className="w-full h-full bg-secondary flex items-center justify-center">
                                  <Music size={16} />
                                </div>
                              )}
                              {isPlayingCurrent ? (
                                <div className="absolute inset-0 bg-black/60 flex items-center justify-center gap-0.5">
                                  {[1, 2, 3].map((i) => (
                                    <motion.div
                                      key={i}
                                      animate={{ height: [3, 12, 3] }}
                                      transition={{
                                        duration: 0.5,
                                        repeat: Infinity,
                                        repeatType: "reverse",
                                        delay: i * 0.1,
                                        ease: "easeInOut",
                                      }}
                                      className="w-1 bg-primary rounded-full"
                                    />
                                  ))}
                                </div>
                              ) : (
                                <div
                                  className={`absolute inset-0 bg-black/40 flex items-center justify-center transition-opacity ${
                                    isCurrent
                                      ? "opacity-100"
                                      : "opacity-0 group-hover/img:opacity-100"
                                  }`}
                                >
                                  <Play
                                    size={16}
                                    className={`fill-white ${
                                      isCurrent ? "text-primary" : "text-white"
                                    }`}
                                  />
                                </div>
                              )}
                            </button>
                            <div className="min-w-0 flex-1">
                              <span
                                className={`block font-medium truncate max-w-[150px] sm:max-w-[200px] md:max-w-[280px] lg:max-w-none transition-colors ${
                                  isCurrent ? "text-primary font-bold" : "text-white"
                                }`}
                              >
                                {item.track.title}
                              </span>
                              <span className="block md:hidden text-sm text-gray-400 truncate">
                                {item.track.artist}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-3 md:px-6 py-3 md:py-4 text-gray-300 hidden md:table-cell truncate max-w-[150px]">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const id = item.track.artist_id || item.track.spotify_artist_id;
                              if (id) {
                                navigate(`/artist/${id}`);
                              } else {
                                navigate(
                                  `/search?q=${encodeURIComponent(item.track.artist)}&type=artist`
                                );
                              }
                            }}
                            className="hover:text-primary hover:underline transition-colors text-left truncate w-full"
                          >
                            {item.track.artist}
                          </button>
                        </td>
                        <td className="px-3 md:px-6 py-3 md:py-4 text-gray-400 hidden lg:table-cell truncate max-w-[120px]">
                          {item.track.album || "-"}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => onAddToPlaylist(item.track_id)}
                              className="p-2 text-gray-400 hover:text-primary hover:bg-primary/10 rounded-full transition-colors"
                              title="Add to Playlist"
                            >
                              <ListPlus size={16} />
                            </button>
                            <button
                              onClick={() => onEdit(item)}
                              className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                              title="Edit Info"
                            >
                              <Edit2 size={16} />
                            </button>
                            <button
                              onClick={() => onDelete(item.id)}
                              className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-full transition-colors"
                              title="Delete File"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </motion.tr>
                    );
                  })}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
          )}
          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-6">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-white/5 rounded-lg disabled:opacity-50 hover:bg-white/10 transition-colors text-white"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 bg-white/5 rounded-lg disabled:opacity-50 hover:bg-white/10 transition-colors text-white"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
};

export default function Library() {
  const { t } = useTranslation();
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [displayMode, setDisplayMode] = useState<"grid" | "list">(
    () => (localStorage.getItem("library:displayMode") as "grid" | "list") || "grid"
  );

  const handleSetDisplayMode = (mode: "grid" | "list") => {
    localStorage.setItem("library:displayMode", mode);
    setDisplayMode(mode);
  };
  const [folders, setFolders] = useState<FolderStructure>({});
  const [loading, setLoading] = useState(true);

  // Navigation State
  const [searchParams, setSearchParams] = useSearchParams();

  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    if (searchParams.get("playlist")) return "playlist";
    if (searchParams.get("source")) return "service";
    return "root";
  });

  const [selectedService, setSelectedService] = useState<string | null>(searchParams.get("source"));
  const [selectedPlaylist, setSelectedPlaylist] = useState<string | null>(
    searchParams.get("playlist")
  );

  // Sync state changes to URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedService) params.set("source", selectedService);
    if (selectedPlaylist) params.set("playlist", selectedPlaylist);
    setSearchParams(params, { replace: true });
  }, [selectedService, selectedPlaylist, setSearchParams]);

  const [searchQuery, setSearchQuery] = useState("");
  const [editingItem, setEditingItem] = useState<LibraryItem | null>(null);

  // Modals state
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deletePlaylistTarget, setDeletePlaylistTarget] = useState<{
    source: string;
    playlist: string;
  } | null>(null);
  const [showRescanModal, setShowRescanModal] = useState(false);
  const [showCreatePlaylistModal, setShowCreatePlaylistModal] = useState(false);

  // Playlist modal state
  const [playlistModalOpen, setPlaylistModalOpen] = useState(false);
  const [selectedTrackIds, setSelectedTrackIds] = useState<string[]>([]);

  // Pagination state (for track list view)
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 50;

  // Initialize: Fetch Folder Structure
  useEffect(() => {
    // Async fetch handlers defined below; intentional effect-driven fetch (pre-TanStack pattern)
    // eslint-disable-next-line react-hooks/immutability
    fetchFolders();

    // Listen for refresh events
    const handleRefresh = () => fetchFolders();
    window.addEventListener("library:refresh", handleRefresh);
    return () => window.removeEventListener("library:refresh", handleRefresh);
  }, []);

  // Fetch items when selection changes or page changes
  useEffect(() => {
    if (viewMode === "playlist") {
      // eslint-disable-next-line react-hooks/immutability
      fetchLibraryItems();
    }
  }, [page, viewMode, selectedService, selectedPlaylist]);

  const fetchFolders = async () => {
    try {
      const res = await api.get("/downloads/library/folders");
      setFolders(res.data);
      setLoading(false);
    } catch (e) {
      console.error("Failed to fetch folders", e);
      setLoading(false);
    }
  };

  const fetchLibraryItems = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      // Build params based on selection

      const params: Record<string, string | number> = { skip, limit };

      if (selectedService) params.source = selectedService;
      if (selectedPlaylist) params.playlist = selectedPlaylist;

      const res = await api.get("/downloads/library", { params });

      if (res.data.items) {
        setItems(res.data.items);
        setTotal(res.data.total);
      } else {
        setItems(res.data);
      }
    } catch (e) {
      console.error("Failed to fetch library items", e);
    } finally {
      setLoading(false);
    }
  };

  const handleServiceClick = (source: string) => {
    setSelectedService(source);
    setViewMode("service");
  };

  const handlePlaylistClick = (playlist: string) => {
    setSelectedPlaylist(playlist);
    setViewMode("playlist");
    setPage(1); // Reset page
  };

  const handleAllTracksClick = () => {
    // Special case: View all tracks for service, ignoring playlist
    // But wait, the backend filter `playlist=__none__` gets uncategorized.
    // If we want ALL tracks from a service regardless of playlist status, we just don't pass `playlist` param.
    // But typically "All Tracks" folder icon means "Everything from this service".
    setSelectedPlaylist(null);
    setViewMode("playlist");
    setPage(1);
  };

  const handleDelete = (id: string) => {
    setDeleteId(id);
  };

  const confirmDelete = async () => {
    if (!deleteId) return;
    try {
      await api.delete(`/downloads/${deleteId}`);
      setItems(items.filter((i) => i.id !== deleteId));
      fetchFolders(); // Update counts/structure if emptiness changes
      toast.success("Track deleted");
    } catch (e) {
      console.error("Failed to delete item", e);
      toast.error("Failed to delete item");
    }
  };

  const handlePlaylistDeleteClick = (e: React.MouseEvent, playlist: string) => {
    e.stopPropagation(); // Don't verify playlist
    if (!selectedService) return;
    setDeletePlaylistTarget({ source: selectedService, playlist });
  };

  const confirmPlaylistDelete = async () => {
    if (!deletePlaylistTarget) return;
    try {
      await api.delete("/downloads/library/playlist", {
        params: {
          source: deletePlaylistTarget.source,
          playlist_name: deletePlaylistTarget.playlist,
        },
      });
      toast.success(`Playlist ${deletePlaylistTarget.playlist} deleted`);
      fetchFolders();
      setDeletePlaylistTarget(null);
    } catch (e) {
      console.error("Failed to delete playlist", e);
      toast.error("Failed to delete playlist");
    }
  };

  const handleRescan = async () => {
    try {
      const res = await api.post("/downloads/rescan");
      toast.success(`Rescan complete. Found ${res.data.rescanned_count} missing files.`);
      setShowRescanModal(false);
      fetchFolders(); // Refresh structure after rescan
      if (viewMode === "playlist") {
        fetchLibraryItems();
      }
    } catch (e) {
      console.error("Rescan failed", e);
      toast.error("Rescan failed");
      setShowRescanModal(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;

    const formData = new FormData(e.target as HTMLFormElement);
    const updates = {
      title: formData.get("title"),
      artist: formData.get("artist"),
      album: formData.get("album"),
      filename: formData.get("filename"),
    };

    try {
      await api.put(`/downloads/library/${editingItem.id}`, updates);
      setEditingItem(null);
      fetchLibraryItems(); // Refresh
      toast.success("Track updated");
    } catch (e) {
      console.error("Failed to update item", e);
      toast.error("Failed to update item");
    }
  };

  const handleCreatePlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    const name = formData.get("name") as string;

    if (!name?.trim()) return;

    try {
      await api.post("/playlists/", { name, public: false });
      toast.success("Playlist created");
      setShowCreatePlaylistModal(false);
      fetchFolders(); // Refresh folders
    } catch (e) {
      console.error("Failed to create playlist", e);
      toast.error("Failed to create playlist");
    }
  };

  // Remove unused navigate
  // const navigate = useNavigate();
  // actually I will replace the block to remove it.

  return (
    <div className="space-y-6 pb-24">
      {/* ... header ... */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            {t("library.title")}
          </h1>
          <p className="text-muted-foreground">{t("library.subtitle")}</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setShowCreatePlaylistModal(true)}
            className="flex items-center gap-2 bg-primary/20 hover:bg-primary/30 text-primary px-4 py-2 rounded-lg border border-primary/20 transition-all active:scale-95 cursor-pointer"
          >
            <ListPlus size={16} />
            {t("library.newPlaylist")}
          </button>

          <button
            onClick={() => setShowRescanModal(true)}
            className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-lg border border-white/10 transition-all active:scale-95 cursor-pointer"
          >
            <RefreshCw size={16} />
            {t("library.rescan")}
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex bg-card/40 rounded-lg p-1 border border-border">
          <button
            onClick={() => handleSetDisplayMode("grid")}
            className={`p-2 rounded-md transition-all cursor-pointer ${
              displayMode === "grid"
                ? "bg-secondary text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="Grid View"
          >
            <LayoutGrid size={18} />
          </button>
          <button
            onClick={() => handleSetDisplayMode("list")}
            className={`p-2 rounded-md transition-all cursor-pointer ${
              displayMode === "list"
                ? "bg-secondary text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="List View"
          >
            <List size={18} />
          </button>
        </div>
      </div>

      <LibraryBreadcrumbs
        viewMode={viewMode}
        selectedService={selectedService}
        selectedPlaylist={selectedPlaylist}
        onRootClick={() => {
          setViewMode("root");
          setSelectedService(null);
          setSelectedPlaylist(null);
        }}
        onServiceClick={() => {
          setViewMode("service");
          setSelectedPlaylist(null);
        }}
      />

      {viewMode === "root" && (
        <RootView folders={folders} onServiceClick={handleServiceClick} displayMode={displayMode} />
      )}
      {viewMode === "service" && selectedService && (
        <ServiceView
          playlists={folders[selectedService] || []}
          onAllTracksClick={handleAllTracksClick}
          onPlaylistClick={handlePlaylistClick}
          onPlaylistDelete={handlePlaylistDeleteClick}
          displayMode={displayMode}
        />
      )}
      {viewMode === "playlist" && (
        <PlaylistView
          items={items}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          selectedPlaylist={selectedPlaylist}
          selectedService={selectedService}
          loading={loading}
          total={total}
          limit={limit}
          page={page}
          setPage={setPage}
          onEdit={setEditingItem}
          onDelete={handleDelete}
          onAddToPlaylist={(trackId) => {
            setSelectedTrackIds([trackId]);
            setPlaylistModalOpen(true);
          }}
          displayMode={displayMode}
        />
      )}

      {/* Edit Modal (Same as before) */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-card border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl"
          >
            <h2 className="text-xl font-bold text-foreground mb-4">Edit Track Info</h2>
            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label
                  htmlFor="edit-title"
                  className="block text-sm font-medium text-muted-foreground mb-1"
                >
                  Title
                </label>
                <input
                  id="edit-title"
                  name="title"
                  defaultValue={editingItem.track.title}
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-white focus:outline-none focus:border-primary/50"
                />
              </div>
              <div>
                <label
                  htmlFor="edit-artist"
                  className="block text-sm font-medium text-muted-foreground mb-1"
                >
                  Artist
                </label>
                <input
                  id="edit-artist"
                  name="artist"
                  defaultValue={editingItem.track.artist}
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-white focus:outline-none focus:border-primary/50"
                />
              </div>
              <div>
                <label
                  htmlFor="edit-album"
                  className="block text-sm font-medium text-muted-foreground mb-1"
                >
                  Album
                </label>
                <input
                  id="edit-album"
                  name="album"
                  defaultValue={editingItem.track.album}
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-white focus:outline-none focus:border-primary/50"
                />
              </div>
              <div>
                <label
                  htmlFor="edit-filename"
                  className="block text-sm font-medium text-muted-foreground mb-1"
                >
                  Filename
                </label>
                <input
                  id="edit-filename"
                  name="filename"
                  defaultValue={editingItem.track.filename}
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-white focus:outline-none focus:border-primary/50"
                />
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="px-4 py-2 hover:bg-white/10 rounded-lg transition-colors text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Create Playlist Modal */}
      {showCreatePlaylistModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-card border border-white/10 rounded-2xl p-6 w-full max-w-sm shadow-2xl"
          >
            <h2 className="text-xl font-bold text-foreground mb-4">Create New Playlist</h2>
            <form onSubmit={handleCreatePlaylist} className="space-y-4">
              <div>
                <label
                  htmlFor="playlist-name"
                  className="block text-sm font-medium text-muted-foreground mb-1"
                >
                  Playlist Name
                </label>
                <input
                  id="playlist-name"
                  name="name"
                  placeholder="My Awesome Playlist"
                  autoFocus
                  className="w-full bg-white/5 border border-white/10 rounded-lg p-2 text-white focus:outline-none focus:border-primary/50"
                />
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreatePlaylistModal(false)}
                  className="px-4 py-2 hover:bg-white/10 rounded-lg transition-colors text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Create
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={confirmDelete}
        title="Delete File"
        message="Are you sure you want to delete this file? This cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />

      {/* Delete Playlist Modal */}
      <ConfirmModal
        isOpen={!!deletePlaylistTarget}
        onClose={() => setDeletePlaylistTarget(null)}
        onConfirm={confirmPlaylistDelete}
        title="Delete Playlist"
        message={`Are you sure you want to delete the playlist "${deletePlaylistTarget?.playlist}"? This will delete all files inside it.`}
        confirmText="Delete Playlist"
        cancelText="Cancel"
        variant="danger"
      />

      {/* Rescan Modal */}
      <ConfirmModal
        isOpen={showRescanModal}
        onClose={() => setShowRescanModal(false)}
        onConfirm={handleRescan}
        title="Rescan Library"
        message="This will check for missing files and re-queue them for download. Are you sure?"
        confirmText="Rescan"
      />

      {/* Add to Playlist Modal */}
      <AddToPlaylistModal
        isOpen={playlistModalOpen}
        onClose={() => setPlaylistModalOpen(false)}
        trackIds={selectedTrackIds}
      />
    </div>
  );
}
