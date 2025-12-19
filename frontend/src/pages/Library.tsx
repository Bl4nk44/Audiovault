import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Trash2,
  Edit2,
  Search,
  Music,
  Folder,
  RefreshCw,
} from "lucide-react";
import { useStore } from "../store/useStore";
import api from "../services/api";
import ConfirmModal from "../components/ui/ConfirmModal";
import toast from "react-hot-toast";
import { SiSpotify, SiYoutube, SiApplemusic, SiTidal } from "react-icons/si";
// Using a generic icon for others
import { FaMusic } from "react-icons/fa";

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
  };
}

interface FolderStructure {
  [source: string]: string[];
}

type ViewMode = "root" | "service" | "playlist";

const SourceIcon = ({
  source,
  size = 24,
}: {
  source: string;
  size?: number;
}) => {
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
        <div
          className="text-[#FF5500] font-bold text-xs"
          style={{ fontSize: size }}
        >
          SC
        </div>
      );
    case "deezer":
      return (
        <div
          className="text-white font-bold text-xs"
          style={{ fontSize: size }}
        >
          DZ
        </div>
      );
    case "amazon_music":
      return (
        <div
          className="text-[#00A8E1] font-bold text-xs"
          style={{ fontSize: size }}
        >
          AM
        </div>
      );
    default:
      return <FaMusic size={size} className="text-gray-400" />;
  }
};

export default function Library() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [folders, setFolders] = useState<FolderStructure>({});
  const [loading, setLoading] = useState(true);

  // Navigation State
  const [viewMode, setViewMode] = useState<ViewMode>("root");
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [selectedPlaylist, setSelectedPlaylist] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const { playTrack, currentTrack, isPlaying, togglePlay } = useStore();
  const [editingItem, setEditingItem] = useState<LibraryItem | null>(null);

  // Modals state
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deletePlaylistTarget, setDeletePlaylistTarget] = useState<{
    source: string;
    playlist: string;
  } | null>(null);
  const [showRescanModal, setShowRescanModal] = useState(false);

  // Pagination state (for track list view)
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 50;

  // Initialize: Fetch Folder Structure
  useEffect(() => {
    fetchFolders();
  }, []);

  // Fetch items when selection changes or page changes
  useEffect(() => {
    if (viewMode === "playlist") {
      fetchLibraryItems();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const params: any = { skip, limit };

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
      await api.delete(`/downloads/remove/${deleteId}`);
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
      toast.success(
        `Rescan complete. Found ${res.data.rescanned_count} missing files.`
      );
      setShowRescanModal(false);
      fetchFolders(); // Refresh structure after rescan
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

  // Breadcrumbs
  const renderBreadcrumbs = () => {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
        <span
          className={`cursor-pointer hover:text-foreground ${
            viewMode === "root" ? "text-foreground font-bold" : ""
          }`}
          onClick={() => {
            setViewMode("root");
            setSelectedService(null);
            setSelectedPlaylist(null);
          }}
        >
          Library
        </span>
        {selectedService && (
          <>
            <span>/</span>
            <span
              className={`cursor-pointer hover:text-foreground ${
                viewMode === "service" ? "text-foreground font-bold" : ""
              }`}
              onClick={() => {
                setViewMode("service");
                setSelectedPlaylist(null);
              }}
            >
              {selectedService.charAt(0).toUpperCase() +
                selectedService.slice(1)}
            </span>
          </>
        )}
        {selectedPlaylist && (
          <>
            <span>/</span>
            <span className="text-foreground font-bold">
              {selectedPlaylist === "__none__"
                ? "Uncategorized"
                : selectedPlaylist}
            </span>
          </>
        )}
      </div>
    );
  };

  // View Components
  const RootView = () => (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {Object.keys(folders).map((source) => (
        <motion.div
          key={source}
          initial="rest"
          whileHover="hover"
          whileTap="tap"
          onClick={() => handleServiceClick(source)}
          className="bg-card/40 border border-border rounded-2xl p-6 cursor-pointer hover:bg-card/60 transition-colors flex flex-col items-center justify-center gap-6 text-center aspect-square group"
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
              {folders[source].length}{" "}
              {folders[source].length === 1 ? "playlist" : "playlists"}
            </p>
            {/* Note: Logic above is rough approx, better to have counts from API */}
          </div>
        </motion.div>
      ))}
    </div>
  );

  const ServiceView = () => {
    const playlists = folders[selectedService!] || [];
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {/* All Tracks Card */}
        <motion.div
          initial="rest"
          whileHover="hover"
          whileTap="tap"
          onClick={handleAllTracksClick}
          className="bg-primary/20 border border-primary/30 rounded-2xl p-6 cursor-pointer hover:bg-primary/30 transition-colors flex flex-col items-center justify-center gap-6 text-center aspect-square"
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
          <h3 className="text-xl font-bold text-white">All Tracks</h3>
        </motion.div>

        {/* Playlist Cards */}
        {playlists.map((playlist) => (
          <motion.div
            key={playlist || "uncategorized"}
            initial="rest"
            whileHover="hover"
            whileTap="tap"
            onClick={() => handlePlaylistClick(playlist || "__none__")}
            className="bg-card/40 border border-border rounded-2xl p-6 cursor-pointer hover:bg-card/60 transition-colors flex flex-col items-center justify-center gap-6 text-center aspect-square relative group"
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
                {playlist || "Uncategorized"}
              </h3>
            </div>

            {/* Delete Playlist Button */}
            {playlist && playlist !== "__none__" && (
              <button
                onClick={(e) => handlePlaylistDeleteClick(e, playlist)}
                className="absolute top-3 right-3 p-2 bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white rounded-full opacity-0 group-hover:opacity-100 transition-all duration-200"
                title="Delete Playlist"
              >
                <Trash2 size={16} />
              </button>
            )}
          </motion.div>
        ))}
      </div>
    );
  };

  const PlaylistView = () => {
    // Standard table view
    const filteredItems = items.filter(
      (item) =>
        item.track.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.track.artist.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const totalPages = Math.ceil(total / limit);

    return (
      <>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">
            {selectedPlaylist === "__none__"
              ? "Uncategorized"
              : selectedPlaylist || `All ${selectedService || ""} Tracks`}
          </h2>
          <div className="relative w-64">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              size={18}
            />
            <input
              type="text"
              placeholder="Search tracks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-full py-2 pl-10 pr-4 text-white focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 text-gray-500">
            Loading tracks...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            No tracks found.
          </div>
        ) : (
          <>
            <div className="bg-black/20 border border-white/5 rounded-2xl overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-white/5 text-gray-400 text-sm uppercase font-medium">
                  <tr>
                    <th className="px-6 py-4">Track</th>
                    <th className="px-6 py-4">Artist</th>
                    <th className="px-6 py-4">Album</th>
                    <th className="px-6 py-4 text-right">Actions</th>
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
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-4">
                              <div
                                className={`relative w-10 h-10 rounded overflow-hidden cursor-pointer group/img shrink-0 ${
                                  isCurrent
                                    ? "shadow-[0_0_10px_rgba(var(--primary-rgb),0.5)]"
                                    : ""
                                }`}
                                onClick={() => {
                                  if (
                                    currentTrack?.id === item.track_id &&
                                    isPlaying
                                  ) {
                                    togglePlay();
                                  } else {
                                    const queue = filteredItems.map((i) => ({
                                      id: i.track_id,
                                      title: i.track.title,
                                      artist: i.track.artist,
                                      cover: i.track.image_url,
                                      source: "local",
                                      album: i.track.album,
                                      filename: i.track.filename,
                                    }));
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
                                      queue
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
                                  <div className="w-full h-full bg-gray-800 flex items-center justify-center">
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
                                        isCurrent
                                          ? "text-primary"
                                          : "text-white"
                                      }`}
                                    />
                                  </div>
                                )}
                              </div>
                              <span
                                className={`font-medium transition-colors ${
                                  isCurrent
                                    ? "text-primary font-bold"
                                    : "text-white"
                                }`}
                              >
                                {item.track.title}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-gray-300">
                            {item.track.artist}
                          </td>
                          <td className="px-6 py-4 text-gray-400">
                            {item.track.album || "-"}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={() => setEditingItem(item)}
                                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                                title="Edit Info"
                              >
                                <Edit2 size={16} />
                              </button>
                              <button
                                onClick={() => handleDelete(item.id)}
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

  return (
    <div className="space-y-6 pb-24">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            My Library
          </h1>
          <p className="text-muted-foreground">Manage your downloaded music.</p>
        </div>

        {/* Rescan Button */}
        <button
          onClick={() => setShowRescanModal(true)}
          className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-lg border border-white/10 transition-all active:scale-95"
        >
          <RefreshCw size={16} />
          Rescan Library
        </button>
      </div>

      {renderBreadcrumbs()}

      {viewMode === "root" && <RootView />}
      {viewMode === "service" && <ServiceView />}
      {viewMode === "playlist" && <PlaylistView />}

      {/* Edit Modal (Same as before) */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-card border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl"
          >
            <h2 className="text-xl font-bold text-foreground mb-4">
              Edit Track Info
            </h2>
            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Title
                </label>
                <input
                  name="title"
                  defaultValue={editingItem.track.title}
                  className="w-full bg-secondary/30 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Artist
                </label>
                <input
                  name="artist"
                  defaultValue={editingItem.track.artist}
                  className="w-full bg-secondary/30 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Album
                </label>
                <input
                  name="album"
                  defaultValue={editingItem.track.album}
                  className="w-full bg-secondary/30 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Filename
                </label>
                <input
                  name="filename"
                  defaultValue={editingItem.track.filename}
                  className="w-full bg-secondary/30 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <p className="text-xs text-yellow-500/80 mt-1">
                  Warning: Changing filename might break playlists if not
                  updated.
                </p>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="px-4 py-2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* Delete Track Modal */}
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
    </div>
  );
}
