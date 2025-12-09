import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, Trash2, Edit2, Search, Music } from "lucide-react";
import { useStore } from "../store/useStore";
import api from "../services/api";

import ConfirmModal from "../components/ui/ConfirmModal";

interface LibraryItem {
  id: string;
  track_id: string;
  status: string;
  file_path: string;
  created_at: string;
  track: {
    title: string;
    artist: string;
    album?: string;
    image_url?: string;
    filename?: string;
  };
}

export default function Library() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const { playTrack, currentTrack, isPlaying, togglePlay } = useStore();
  const [editingItem, setEditingItem] = useState<LibraryItem | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 50;

  const fetchLibrary = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      const res = await api.get("/downloads/library", {
        params: { skip, limit },
      });
      // Handle new response structure { items, total, ... }
      if (res.data.items) {
        setItems(res.data.items);
        setTotal(res.data.total);
      } else {
        // Fallback for old API if needed (though we just changed it)
        setItems(res.data);
      }
    } catch (e) {
      console.error("Failed to fetch library", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLibrary();
  }, [page]); // Refetch when page changes

  const handleDelete = (id: string) => {
    setDeleteId(id);
  };

  const confirmDelete = async () => {
    if (!deleteId) return;
    try {
      await api.delete(`/downloads/remove/${deleteId}`);
      setItems(items.filter((i) => i.id !== deleteId));
    } catch (e) {
      console.error("Failed to delete item", e);
      alert("Failed to delete item");
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
      fetchLibrary(); // Refresh to show changes
    } catch (e) {
      console.error("Failed to update item", e);
      alert("Failed to update item");
    }
  };

  // Client-side filtering for current page (Note: ideal would be server-side search)
  const filteredItems = items.filter(
    (item) =>
      item.track.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.track.artist.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6 pb-24">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            My Library
          </h1>
          <p className="text-gray-400">
            Manage your downloaded tracks ({total} items).
          </p>
        </div>
        <div className="relative w-64">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            size={18}
          />
          <input
            type="text"
            placeholder="Search current page..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-full py-2 pl-10 pr-4 text-white focus:outline-none focus:border-primary/50 transition-colors"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-20 text-gray-500">
          Loading library...
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          {searchQuery
            ? "No tracks found matching your search."
            : "Your library is empty or this page has no items."}
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
                  {filteredItems.map((item) => (
                    <motion.tr
                      key={item.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="group hover:bg-white/5 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-4">
                          <div
                            className="relative w-10 h-10 rounded overflow-hidden cursor-pointer group/img"
                            onClick={() => {
                              if (
                                currentTrack?.id === item.track_id &&
                                isPlaying
                              ) {
                                togglePlay();
                              } else {
                                // Create queue from filtered items
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
                            <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover/img:opacity-100 transition-opacity">
                              <Play
                                size={16}
                                className="text-white fill-white"
                              />
                            </div>
                          </div>
                          <span className="font-medium text-white">
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
                  ))}
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

      {/* Edit Modal */}
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
    </div>
  );
}
