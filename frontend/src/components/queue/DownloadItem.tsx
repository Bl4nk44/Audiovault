import {
  AlertCircle,
  CheckCircle,
  Loader2,
  Music,
  Trash2,
  Pause,
  Play,
  RotateCcw,
} from "lucide-react";

import { motion } from "framer-motion";
import { cn } from "../../lib/utils";

import { useStore } from "../../store/useStore";

import { useState } from "react";
import ConfirmModal from "../ui/ConfirmModal";
import { downloadsApi } from "../../api/downloads";

import { type Track } from "../../types";

interface DownloadItemProps {
  item: {
    id: string;
    track_id?: string;
    track: {
      title: string;
      artist: string;
      image_url?: string;
      filename?: string;
    };
    status: string;
    progress: number;
    error_message?: string;
  };
  queue?: Track[]; // Allow queue context
}

export default function DownloadItem({ item, queue }: DownloadItemProps) {
  const {
    playTrack,
    pauseDownload,
    resumeDownload,
    retryDownload,
    removeFromQueue,
  } = useStore();
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const handlePlay = () => {
    if (item.status === "completed") {
      playTrack(
        {
          id: item.track_id || item.id,
          title: item.track.title,
          artist: item.track.artist,
          cover: item.track.image_url,
          source: "download",
          filename: item.track.filename,
        },
        queue
      );
    }
  };

  const getStatusBadge = () => {
    switch (item.status) {
      case "completed":
        return (
          <span className="px-2 py-1 rounded-full bg-primary/20 text-primary text-xs font-bold border border-primary/20 flex items-center gap-1">
            <CheckCircle size={12} /> Completed
          </span>
        );
      case "failed":
        return (
          <span className="px-2 py-1 rounded-full bg-destructive/20 text-destructive text-xs font-medium border border-destructive/20 flex items-center gap-1">
            <AlertCircle size={12} /> Failed
          </span>
        );
      case "downloading":
        return (
          <span className="px-2 py-1 rounded-full bg-primary/20 text-primary text-xs font-medium border border-primary/20 flex items-center gap-1 animate-pulse">
            <Loader2 size={12} className="animate-spin" /> Downloading
          </span>
        );
      case "processing":
        return (
          <span className="px-2 py-1 rounded-full bg-primary/20 text-primary text-xs font-medium border border-primary/20 flex items-center gap-1">
            <Loader2 size={12} className="animate-spin" /> Processing
          </span>
        );
      case "paused":
        return (
          <span className="px-2 py-1 rounded-full bg-yellow-500/20 text-yellow-400 text-xs font-medium border border-yellow-500/20 flex items-center gap-1">
            <Pause size={12} /> Paused
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 rounded-full bg-muted text-muted-foreground text-xs font-medium border border-white/5">
            Pending
          </span>
        );
    }
  };

  const isDownloading = item.status === "downloading";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
      onClick={handlePlay}
      className={cn(
        "group relative bg-card/50 backdrop-blur-md rounded-2xl p-4 flex items-center gap-5 transition-all shadow-lg overflow-hidden border border-white/5",
        isDownloading
          ? "border-primary/50 shadow-[0_0_20px_rgba(var(--primary),0.15)] bg-card/80"
          : "hover:border-white/10",
        item.status === "completed"
          ? "cursor-pointer hover:bg-white/5 hover:scale-[1.01]"
          : ""
      )}
    >
      {/* Active Download Background Gradient */}
      {isDownloading && (
        <div className="absolute inset-0 bg-linear-to-r from-primary/5 to-transparent pointer-events-none" />
      )}

      {/* Cover Image */}
      <div
        className={cn(
          "w-16 h-16 bg-black/40 rounded-xl overflow-hidden shrink-0 border shadow-md relative group-hover:scale-105 transition-transform duration-300 z-10",
          isDownloading ? "border-primary/30" : "border-white/10"
        )}
      >
        {item.track.image_url ? (
          <img
            src={item.track.image_url}
            alt={item.track.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            <Music size={24} />
          </div>
        )}

        {/* Progress Overlay for Image */}
        {isDownloading && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center backdrop-blur-[1px]">
            <span className="text-xs font-bold text-primary">
              {Math.round(item.progress)}%
            </span>
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0 space-y-1 z-10">
        <div className="flex justify-between items-center">
          <div className="flex-1 min-w-0 mr-4">
            <h4 className="font-bold text-white truncate text-lg leading-tight">
              {item.track.title}
            </h4>
            <p className="text-sm text-gray-400 truncate">
              {item.track.artist}
            </p>
          </div>
          <div className="shrink-0">{getStatusBadge()}</div>
        </div>

        {/* Progress Bar */}
        {isDownloading && (
          <div className="relative h-2 w-full bg-black/20 rounded-full overflow-hidden mt-3 border border-white/5">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${item.progress}%` }}
              transition={{ ease: "linear" }}
              className="h-full bg-linear-to-r from-primary/80 to-primary shadow-[0_0_10px_rgba(34,197,94,0.5)]"
            />
          </div>
        )}

        {/* Error Message */}
        {item.status === "failed" && (
          <p className="text-xs text-red-400 mt-1 flex items-center gap-1 bg-red-500/10 p-1 rounded px-2 w-fit">
            {item.error_message}
          </p>
        )}
      </div>

      {/* Action Icon (Play/Retry etc) */}
      <div className="flex items-center gap-2 shrink-0 z-10">
        {item.status === "completed" && (
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-primary/20 hover:scale-110 transition-all">
              <CheckCircle className="text-primary" size={20} />
            </div>
          </div>
        )}

        {/* Control Actions */}
        {item.status === "downloading" && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              pauseDownload(item.id);
            }}
            className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-yellow-500/20 hover:text-yellow-400 text-gray-400 transition-all"
            title="Pause"
          >
            <Pause size={20} />
          </button>
        )}

        {item.status === "paused" && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              resumeDownload(item.id);
            }}
            className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-primary/20 hover:text-primary text-gray-400 transition-all"
            title="Resume"
          >
            <Play size={20} />
          </button>
        )}

        {item.status === "failed" && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              e.nativeEvent.stopImmediatePropagation();
              retryDownload(item.id);
            }}
            className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-primary/20 hover:text-primary text-gray-400 transition-all"
            title="Retry"
          >
            <RotateCcw size={20} />
          </button>
        )}

        {(item.status === "completed" ||
          item.status === "failed" ||
          item.status === "paused") && (
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
                setShowDeleteModal(true);
              }}
              className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-red-500/20 hover:text-red-400 text-gray-400 transition-all"
              title="Delete file"
            >
              <Trash2 size={20} />
            </button>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => {
          removeFromQueue(item.id);
          downloadsApi.remove(item.id);
          setShowDeleteModal(false);
        }}
        title="Delete File"
        message="Are you sure you want to delete this file? This cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
    </motion.div>
  );
}
