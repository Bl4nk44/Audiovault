import React, { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import { useTranslation } from "react-i18next";
import { IoAdd, IoCheckmark, IoClose, IoMusicalNote } from "react-icons/io5";
import { playlistsApi } from "../api/playlists";
import type { Playlist } from "../types";

interface AddToPlaylistModalProps {
  isOpen: boolean;
  onClose: () => void;
  trackIds: string[]; // IDs of tracks to add
}

const AddToPlaylistModal: React.FC<AddToPlaylistModalProps> = ({ isOpen, onClose, trackIds }) => {
  const { t } = useTranslation();
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState("");

  // Feedback state
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchPlaylists = async () => {
      setLoading(true);
      try {
        const data = await playlistsApi.getAll();
        setPlaylists(data);
      } catch (err) {
        console.error("Failed to fetch playlists", err);
        setErrorMsg(t("playlist.fetch.error", "Failed to load playlists"));
      } finally {
        setLoading(false);
      }
    };

    if (isOpen) {
      fetchPlaylists();
      // Reset transient form state when the modal opens — gated on isOpen, not derivable in render
      /* eslint-disable react-hooks/set-state-in-effect */
      setSuccessMsg(null);
      setErrorMsg(null);
      setCreating(false);
      setNewPlaylistName("");
      /* eslint-enable react-hooks/set-state-in-effect */
    }
  }, [isOpen, t]);

  const handleCreatePlaylist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlaylistName.trim()) return;

    try {
      const newPl = await playlistsApi.create({ name: newPlaylistName, public: false });
      setPlaylists([...playlists, { ...newPl, title: newPl.name, source: "local" }]);
      setNewPlaylistName("");
      setCreating(false);
      // Automatically add to the new playlist? Optional, but UX friendly.
      // Let's rely on user clicking the list item for now to avoid confusion.
    } catch (err) {
      console.error("Failed to create playlist", err);
      setErrorMsg(t("playlist.create.error", "Failed to create playlist"));
    }
  };

  const handleAddToPlaylist = async (playlistId: string) => {
    try {
      const response = await playlistsApi.addTracks(playlistId, trackIds);

      const { added_count, duplicate_count } = response;

      if (added_count > 0) {
        toast.success(
          t("playlist.add.success", `Added ${added_count} tracks to playlist`, {
            count: added_count,
          })
        );
      }

      if (duplicate_count > 0) {
        toast.error(
          t("playlist.add.duplicates", `${duplicate_count} tracks were already in the playlist`, {
            count: duplicate_count,
          }),
          {
            icon: "ℹ️",
            duration: 4000,
          }
        );
      }

      // Trigger refresh
      globalThis.dispatchEvent(new CustomEvent("library:refresh"));

      if (added_count > 0) {
        setTimeout(() => {
          onClose();
          setSuccessMsg(null);
        }, 1500);
      }
    } catch (err) {
      console.error("Failed to add tracks", err);
      setErrorMsg(t("playlist.add.error", "Failed to add tracks"));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-md bg-zinc-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5 bg-zinc-800/50">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <IoMusicalNote className="text-primary" />
            {t("playlist.modal.title", "Add to Playlist")}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
          >
            <IoClose size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
          {errorMsg && (
            <div className="mb-4 p-3 bg-red-500/10 text-red-500 text-sm rounded-lg border border-red-500/20">
              {errorMsg}
            </div>
          )}
          {successMsg && (
            <div className="mb-4 p-3 bg-green-500/10 text-green-500 text-sm rounded-lg border border-green-500/20 flex items-center gap-2">
              <IoCheckmark /> {successMsg}
            </div>
          )}

          {/* Create New Playlist Section */}
          {creating ? (
            <form
              onSubmit={handleCreatePlaylist}
              className="mb-4 p-3 bg-white/5 rounded-lg border border-white/10"
            >
              <input
                type="text"
                autoFocus
                value={newPlaylistName}
                onChange={(e) => setNewPlaylistName(e.target.value)}
                placeholder={t("playlist.create.placeholder", "Playlist name")}
                className="w-full bg-zinc-950 border border-white/10 rounded px-3 py-2 text-white focus:outline-none focus:border-primary mb-2"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setCreating(false)}
                  className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={!newPlaylistName.trim()}
                  className="px-3 py-1.5 text-sm bg-primary hover:opacity-80 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t("common.create", "Create")}
                </button>
              </div>
            </form>
          ) : (
            <button
              onClick={() => setCreating(true)}
              className="w-full flex items-center gap-3 p-3 mb-2 rounded-lg hover:bg-white/5 text-left group transition-colors border border-dashed border-white/10 hover:border-primary/50"
            >
              <div className="w-10 h-10 flex items-center justify-center bg-white/5 rounded group-hover:bg-primary/20 text-white/50 group-hover:text-primary transition-colors">
                <IoAdd size={24} />
              </div>
              <span className="font-medium text-zinc-300 group-hover:text-white">
                {t("playlist.create.new", "Create New Playlist")}
              </span>
            </button>
          )}

          <div className="space-y-1">
            {loading && <div className="text-center py-4 text-zinc-500">Loading layouts...</div>}

            {!loading && playlists.length === 0 && !creating && (
              <div className="text-center py-4 text-zinc-500 text-sm">
                No playlists found. Create one above!
              </div>
            )}

            {!loading &&
              playlists.length > 0 &&
              playlists.map((pl) => (
                <button
                  key={pl.id}
                  onClick={() => handleAddToPlaylist(pl.id)}
                  className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 text-left transition-colors group"
                >
                  {/* Placeholder Cover */}
                  <div className="w-10 h-10 flex items-center justify-center bg-zinc-800 rounded text-zinc-600 group-hover:text-zinc-400">
                    <IoMusicalNote size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white truncate">{pl.title || pl.name}</h3>
                    <p className="text-xs text-zinc-500">{pl.tracks_count || 0} tracks</p>
                  </div>
                </button>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AddToPlaylistModal;
