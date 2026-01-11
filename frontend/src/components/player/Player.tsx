import { useRef, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useStore } from "../../store/useStore";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Maximize2,
  X,
  Activity,
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils";

declare global {
  interface Window {
    webkitAudioContext: typeof AudioContext;
  }
}

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
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showVisualizer, setShowVisualizer] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const hasRecordedRef = useRef(false);

  // Reset recording flag on track change
  useEffect(() => {
    hasRecordedRef.current = false;
  }, [currentTrack]);

  // Record history
  useEffect(() => {
    if (currentTime > 30 && !hasRecordedRef.current && currentTrack) {
      hasRecordedRef.current = true;
      // Fire and forget
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

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const [imgError, setImgError] = useState(false);

  // Reset image error on track change
  useEffect(() => {
    setImgError(false);
  }, [currentTrack]);

  // Audio Context & Visualizer
  useEffect(() => {
    if (!audioRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;

    const initAudio = async () => {
      try {
        // iOS Fix: Web Audio API intercepts native audio stream, causing background playback to fail.
        // We must disable the visualizer on iOS to keep native <audio> behavior intact.
        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        if (isIOS) return;

        if (!audioContextRef.current) {
          const AudioContextClass =
            window.AudioContext || window.webkitAudioContext;
          audioContextRef.current = new AudioContextClass();
          analyserRef.current = audioContextRef.current.createAnalyser();
          analyserRef.current.fftSize = 256;

          // Connect source only once
          if (audioRef.current && !sourceRef.current) {
            sourceRef.current =
              audioContextRef.current.createMediaElementSource(
                audioRef.current
              );
            sourceRef.current.connect(analyserRef.current);
            analyserRef.current.connect(audioContextRef.current.destination);
          }
        }

        // Resume context if suspended (browser policy)
        if (audioContextRef.current.state === "suspended") {
          await audioContextRef.current.resume();
        }

        const analyser = analyserRef.current;
        if (!analyser) return;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
          animationId = requestAnimationFrame(draw);
          analyser.getByteFrequencyData(dataArray);

          ctx.clearRect(0, 0, canvas.width, canvas.height);

          // Ambient Wave Effect
          const width = canvas.width;
          const height = canvas.height;
          const barWidth = (width / bufferLength) * 2.5;

          // Create gradient based on frequency intensity
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length;

          // Dynamic background tint based on bass
          ctx.fillStyle = `rgba(20, 0, 40, ${(average / 255) * 0.2})`;
          ctx.fillRect(0, 0, width, height);

          let x = 0;

          ctx.beginPath();
          ctx.moveTo(0, height);

          for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * height * 0.8; // Increased height multiplier

            // Smooth curve
            const y = height - barHeight;

            if (i === 0) {
              ctx.moveTo(x, y);
            } else {
              const prevX = x - barWidth;
              const prevY = height - (dataArray[i - 1] / 255) * height * 0.5;
              const cpX = (prevX + x) / 2;
              const cpY = (prevY + y) / 2;
              ctx.quadraticCurveTo(cpX, cpY, x, y);
            }

            x += barWidth;
          }

          ctx.lineTo(width, height);
          ctx.lineTo(0, height);
          ctx.closePath();

          const gradient = ctx.createLinearGradient(0, height * 0.5, 0, height);
          gradient.addColorStop(0, "rgba(34, 197, 94, 0.8)"); // Green top (more visible)
          gradient.addColorStop(0.5, "rgba(168, 85, 247, 0.6)"); // Purple middle
          gradient.addColorStop(1, "rgba(59, 130, 246, 0.4)"); // Blue bottom

          ctx.fillStyle = gradient;
          ctx.fill();
        };
        draw();
      } catch (e) {
        console.error("Audio context error:", e);
      }
    };

    // Initialize on play if not already
    if (isPlaying) {
      initAudio();
    }

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [isPlaying, showVisualizer]);

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

  // Media Session API Support
  useEffect(() => {
    if ("mediaSession" in navigator && currentTrack) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: currentTrack.title,
        artist: currentTrack.artist,
        album: currentTrack.album || "Audiovault",
        artwork: [
          {
            src: currentTrack.cover || "/icon-192.png", // Fallback icon needed
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
      navigator.mediaSession.setActionHandler("previoustrack", () => {
        prevTrack();
      });
      navigator.mediaSession.setActionHandler("nexttrack", () => {
        nextTrack();
      });
      navigator.mediaSession.setActionHandler("seekto", (details) => {
        if (details.seekTime && audioRef.current) {
          audioRef.current.currentTime = details.seekTime;
          setCurrentTime(details.seekTime);
        }
      });
    }
  }, [currentTrack, isPlaying, togglePlay, nextTrack, prevTrack]);

  const formatTime = (time: number) => {
    if (isNaN(time)) return "0:00";
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  if (!currentTrack) return null;

  // Construct stream URL
  // Use filename if available (for downloads), otherwise fallback to ID (might not work if file has extension)
  // Ideally backend should handle ID lookup if filename is missing, but filename is safer.

  // Fix: Remove /api/v1 from base URL for static files served from root /stream
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
      {/* Global Visualizer Background */}
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
        {/* Track Info */}
        <div
          className={cn(
            "flex items-center gap-3 md:gap-4 transition-all overflow-hidden",
            isExpanded ? "flex-col text-center mb-8 w-full" : "flex-1 w-0 min-w-0 md:w-1/3 md:min-w-0"
          )}
        >
          <div
            className={cn(
              "relative overflow-hidden rounded-xl shadow-2xl shrink-0",
              isExpanded
                ? "w-64 h-64 md:w-80 md:h-80 mb-6 aspect-square"
                : "w-10 h-10 md:w-14 md:h-14"
            )}
          >
            {currentTrack.cover && !imgError ? (
              <img
                src={currentTrack.cover}
                alt={currentTrack.title}
                className="w-full h-full object-cover"
                onError={() => setImgError(true)}
              />
            ) : (
              <div className="w-full h-full bg-linear-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                <span className="text-2xl">🎵</span>
              </div>
            )}
          </div>
          <div className={cn("min-w-0", isExpanded ? "w-full" : "flex-1")}>
            <h3
              className={cn(
                "font-bold text-white truncate",
                isExpanded ? "text-3xl" : "text-sm md:text-base"
              )}
            >
              {currentTrack.title}
            </h3>
            <p
              className={cn(
                "text-gray-400 truncate",
                isExpanded ? "text-xl" : "text-xs"
              )}
            >
              {currentTrack.artist}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div
          className={cn(
            "flex flex-col items-center gap-2",
            isExpanded ? "w-full max-w-lg mx-auto" : "flex-1"
          )}
        >
          <div className="flex items-center gap-4 md:gap-6">
            <button
              onClick={prevTrack}
              className={cn(
                "text-gray-400 hover:text-white transition-colors hover:scale-110 active:scale-95",
                !isExpanded && "hidden md:block" // Hide Prev on mobile mini
              )}
            >
              <SkipBack size={isExpanded ? 32 : 24} />
            </button>
            <button
              onClick={togglePlay}
              className={cn(
                "rounded-full bg-primary text-black flex items-center justify-center hover:scale-105 transition-all shadow-[0_0_15px_hsl(var(--primary)/0.5)]",
                isExpanded ? "w-16 h-16" : "w-10 h-10 md:w-10 md:h-10 shrink-0"
              )}
            >
              {isPlaying ? (
                <Pause size={isExpanded ? 32 : 20} fill="currentColor" />
              ) : (
                <Play
                  size={isExpanded ? 32 : 20}
                  fill="currentColor"
                  className="ml-1"
                />
              )}
            </button>
            <button
              onClick={nextTrack}
              className={cn(
                "text-gray-400 hover:text-white transition-colors hover:scale-110 active:scale-95",
                !isExpanded && "hidden md:block" // Hide Next on mobile mini
              )}
            >
              <SkipForward size={isExpanded ? 32 : 24} />
            </button>
          </div>

          {/* Progress Bar - Show on mobile expanded or desktop only */}
          <div
            className={cn(
              "w-full flex items-center gap-3 text-xs text-gray-400 font-medium",
              !isExpanded && "hidden md:flex"
            )}
          >
            <span>{formatTime(currentTime)}</span>
            <input
              type="range"
              min={0}
              max={duration || 0}
              value={currentTime}
              onChange={(e) => {
                const newTime = Number(e.target.value);
                if (audioRef.current) {
                  audioRef.current.currentTime = newTime;
                  setCurrentTime(newTime);
                }
              }}
              className="flex-1 h-1 bg-white/10 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full hover:[&::-webkit-slider-thumb]:bg-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
              aria-label="Seek slider"
              style={{
                backgroundSize: `${
                  (currentTime / (duration || 1)) * 100
                }% 100%`,
                backgroundImage: `linear-gradient(to right, hsl(var(--primary)) 0%, hsl(var(--primary)) 100%)`,
                backgroundRepeat: "no-repeat",
              }}
            />
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Volume & Expand/Close */}
        <div
          className={cn(
            "flex items-center justify-end gap-2 md:gap-4",
            isExpanded
              ? "absolute top-6 right-6 md:top-8 md:right-8"
              : "w-auto md:w-1/3"
          )}
        >
          {/* Hide Volume on Mobile Mini */}
          <div
            className={cn(
              "flex items-center gap-2 group",
              !isExpanded && "hidden md:flex"
            )}
          >
            <button
              onClick={() => setVolume(volume === 0 ? 1 : 0)}
              className="text-gray-400 hover:text-white"
            >
              {volume === 0 ? <VolumeX size={20} /> : <Volume2 size={20} />}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={volume}
              onChange={(e) => setVolume(Number.parseFloat(e.target.value))}
              className="w-20 md:w-24 h-1 bg-white/10 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full hover:[&::-webkit-slider-thumb]:bg-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
              aria-label="Volume slider"
              style={{
                backgroundSize: `${volume * 100}% 100%`,
                backgroundImage: `linear-gradient(to right, white 0%, white 100%)`,
                backgroundRepeat: "no-repeat",
              }}
            />
          </div>

          <button
            onClick={() => setShowVisualizer(!showVisualizer)}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full transition-all text-sm font-medium",
              showVisualizer
                ? "text-primary bg-primary/10 border border-primary/20 shadow-[0_0_10px_hsl(var(--primary)/0.2)]"
                : "text-gray-400 bg-white/5 border border-white/5 hover:bg-white/10 hover:text-white",
              !isExpanded && "hidden md:flex" // Hide Visualizer toggle on mini player mobile
            )}
            title="Toggle Visualizer"
            style={{
              display: /iPhone|iPad|iPod/i.test(navigator.userAgent)
                ? "none"
                : "flex",
            }}
          >
            <Activity size={16} />
            <span>Visualizer</span>
          </button>
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
        crossOrigin={/iPhone|iPad|iPod/i.test(navigator.userAgent) ? undefined : "anonymous"}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => togglePlay()}
        playsInline
        preload="auto"
      >
        <track kind="captions" src="" label="English" />
      </audio>
    </motion.div>
  );
}
