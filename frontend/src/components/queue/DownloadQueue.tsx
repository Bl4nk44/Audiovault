import { useEffect, useState, useCallback } from "react";
import api from "../../services/api";
import DownloadItem from "./DownloadItem";
import { Loader2, Music2, History } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { Download } from "../../types";

import { useStore } from "../../store/useStore";

export default function DownloadQueue() {
  const [queue, setQueue] = useState<Download[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { addNotification } = useStore();

  const fetchQueue = useCallback(async () => {
    try {
      const response = await api.get("/downloads/queue");
      setQueue(response.data || []);
    } catch (error) {
      console.error("Failed to fetch queue", error);
      addNotification("error", "Failed to refresh download queue");
    } finally {
      setIsLoading(false);
    }
  }, [addNotification]);

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 2000);

    const handleProgress = () => {
      // Logic to update local state optimistically or via store
      // For now we rely on store updates via WebSocket or polling,
      // but we can also use this event to animate progress bars locally.
      // globalThis.dispatchEvent(new CustomEvent('update-progress', { detail: e.detail }));
    };

    globalThis.addEventListener(
      "download:progress",
      handleProgress as EventListener
    );
    globalThis.addEventListener("download:completed", fetchQueue);
    globalThis.addEventListener("download:error", fetchQueue);

    return () => {
      clearInterval(interval);
      globalThis.removeEventListener(
        "download:progress",
        handleProgress as EventListener
      );
      globalThis.removeEventListener("download:completed", fetchQueue);
      globalThis.removeEventListener("download:error", fetchQueue);
    };
  }, [fetchQueue]);

  if (isLoading) {
    return (
      <div className="flex justify-center p-12">
        <Loader2 className="animate-spin text-primary" size={40} />
      </div>
    );
  }

  if (!queue || queue.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center py-20 px-4 rounded-3xl bg-white/5 border border-white/10 backdrop-blur-md text-center"
      >
        <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-6 shadow-inner">
          <Music2 size={40} className="text-gray-500" />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">Queue is empty</h3>
        <p className="text-gray-400 max-w-sm">
          Start downloading tracks to see them appear here.
        </p>
      </motion.div>
    );
  }

  const handleClearHistory = async () => {
    try {
      await api.post("/downloads/clear-history");
      fetchQueue();
      addNotification("success", "History cleared");
    } catch (error) {
      console.error("Failed to clear history", error);
      addNotification("error", "Failed to clear history");
    }
  };

  return (
    <div className="space-y-4 pb-20">
      <div className="flex justify-end mb-4">
        <button
          onClick={handleClearHistory}
          className="flex items-center gap-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-gray-400 hover:text-white transition-colors"
        >
          <History size={16} />
          <span>Clear History</span>
        </button>
      </div>
      <AnimatePresence mode="popLayout">
        {queue.map((item) => {
          const tracksQueue = queue.map((q) => ({
            id: q.track?.id || q.id, // Fallback for safety
            title: q.track.title,
            artist: q.track.artist,
            cover: q.track.image_url,
            source: "download",
            filename: q.track.filename,
          }));
          return <DownloadItem key={item.id} item={item} queue={tracksQueue} />;
        })}
      </AnimatePresence>
    </div>
  );
}
