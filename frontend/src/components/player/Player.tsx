import { useRef, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useStore } from "../../store/useStore";
import { Maximize2, X } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils";
import { useAudioVisualizer } from "../../hooks/useAudioVisualizer";
import { TrackInfo } from "./TrackInfo";
import { PlayerControls } from "./PlayerControls";
import { ProgressBar } from "./ProgressBar";
import { VolumeControl } from "./VolumeControl";
import { VisualizerToggle } from "./VisualizerToggle";

export default function Player() {
  const {
    currentTrack,
    isPlaying,
    togglePlay,
    volume,
    setVolume,
    nextTrack,
    prevTrack,
  } = useStore();

  const audioRef = useRef<HTMLAudioElement>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showVisualizer, setShowVisualizer] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const hasRecordedRef = useRef(false);

  // Audio Visualizer Hook
  const canvasRef = useAudioVisualizer(currentTrack, isPlaying && showVisualizer);

  // Reset recording flag on track change
  useEffect(() => {
    hasRecordedRef.current = false;
  }, [currentTrack]);

  // Record history
  useEffect(() => {
    if (currentTime > 30 && !hasRecordedRef.current && currentTrack) {
      hasRecordedRef.current = true;
      import("../../services/api").then((module) => {
        module.default
          .post("/history/record", {
            track_id: currentTrack.id,
            duration_played: 30,
          })
          .catch((err) => console.error("Failed to record history", err));
      });
    }
  }, [currentTime, currentTrack]);

  // Playback Control
  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.play().catch((e) => console.error("Play error:", e));
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, currentTrack]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      setDuration(audioRef.current.duration || 0);
    }
  };

  const handleSeek = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  // Media Session API Support
  useEffect(() => {
    if ("mediaSession" in globalThis.navigator && currentTrack) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: currentTrack.title,
        artist: currentTrack.artist,
        album: currentTrack.album || "Audiovault",
        artwork: [
          {
            src: currentTrack.cover || "/icon-192.png",
            sizes: "512x512",
            type: "image/jpeg",
          },
        ],
      });

      navigator.mediaSession.setActionHandler("play", () => {
        if (!isPlaying) togglePlay();
      });
      navigator.mediaSession.setActionHandler("pause", () => {
        if (isPlaying) togglePlay();
      });
      navigator.mediaSession.setActionHandler("previoustrack", prevTrack);
      navigator.mediaSession.setActionHandler("nexttrack", nextTrack);
      navigator.mediaSession.setActionHandler("seekto", (details) => {
        if (details.seekTime && audioRef.current) {
          audioRef.current.currentTime = details.seekTime;
          setCurrentTime(details.seekTime);
        }
      });
    }
  }, [currentTrack, isPlaying, togglePlay, nextTrack, prevTrack]);

  if (!currentTrack) return null;

  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
  const baseUrl = apiUrl.replace(/\/api\/v1\/?$/, "");

  const streamUrl = currentTrack.filename
    ? `${baseUrl}/stream/${currentTrack.filename
        .split("/")
        .map(encodeURIComponent)
        .join("/")}`
    : `${apiUrl}/stream/${currentTrack.id}.mp3`;

  return (
    <motion.div
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      exit={{ y: 100 }}
      className={cn(
        "fixed left-0 right-0 z-40 transition-all duration-500 ease-in-out md:left-78",
        isExpanded
          ? "top-0 bottom-0 h-dvh bg-black/95 backdrop-blur-3xl md:left-0"
          : "bottom-20 md:bottom-3 h-16 md:h-24 bg-black/80 md:bg-black/60 backdrop-blur-xl border-t border-white/10 md:rounded-b-3xl"
      )}
    >
      {showVisualizer &&
        createPortal(
          <canvas
            ref={canvasRef}
            width={window.innerWidth}
            height={window.innerHeight}
            className="fixed inset-0 w-full h-full pointer-events-none z-0 opacity-50 mix-blend-screen blur-sm"
          />,
          document.body
        )}

      <div
        className={cn(
          "container mx-auto h-full flex flex-col",
          isExpanded
            ? "justify-center p-6 md:p-8"
            : "flex-row items-center justify-between px-3 md:px-4"
        )}
      >
        <TrackInfo currentTrack={currentTrack} isExpanded={isExpanded} />

        <div
          className={cn(
            "flex flex-col items-center gap-2",
            isExpanded ? "w-full max-w-lg mx-auto" : "flex-1"
          )}
        >
          <PlayerControls
            isPlaying={isPlaying}
            togglePlay={togglePlay}
            nextTrack={nextTrack}
            prevTrack={prevTrack}
            isExpanded={isExpanded}
          />
          <ProgressBar
            currentTime={currentTime}
            duration={duration}
            onSeek={handleSeek}
            isExpanded={isExpanded}
          />
        </div>

        <div
          className={cn(
            "flex items-center justify-end gap-2 md:gap-4",
            isExpanded
              ? "absolute top-6 right-6 md:top-8 md:right-8"
              : "w-auto md:w-1/3"
          )}
        >
          <VolumeControl
            volume={volume}
            setVolume={setVolume}
            isExpanded={isExpanded}
          />

          <VisualizerToggle
            showVisualizer={showVisualizer}
            setShowVisualizer={setShowVisualizer}
            isExpanded={isExpanded}
          />

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-400 hover:text-white p-2 hover:bg-white/10 rounded-full transition-colors"
            aria-label={isExpanded ? "Collapse player" : "Expand player"}
          >
            {isExpanded ? <X size={24} /> : <Maximize2 size={20} />}
          </button>
        </div>
      </div>

      <audio
        ref={audioRef}
        src={streamUrl}
        crossOrigin={
          /iPhone|iPad|iPod/i.test(navigator.userAgent) ? undefined : "anonymous"
        }
        onTimeUpdate={handleTimeUpdate}
        onEnded={togglePlay} // changed from arrow function to direct ref
        preload="auto"
      >
        <track kind="captions" src="" label="English" />
      </audio>
    </motion.div>
  );
}
