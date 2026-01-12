import { Play, Pause, SkipBack, SkipForward } from "lucide-react";
import { cn } from "../../lib/utils";

interface PlayerControlsProps {
  isPlaying: boolean;
  togglePlay: () => void;
  nextTrack: () => void;
  prevTrack: () => void;
  isExpanded: boolean;
}

export function PlayerControls({
  isPlaying,
  togglePlay,
  nextTrack,
  prevTrack,
  isExpanded,
}: Readonly<PlayerControlsProps>) {
  return (
    <div className="flex items-center gap-4 md:gap-6">
      <button
        onClick={prevTrack}
        className={cn(
          "text-gray-400 hover:text-white transition-colors hover:scale-110 active:scale-95",
          !isExpanded && "hidden md:block"
        )}
        aria-label="Previous track"
      >
        <SkipBack size={isExpanded ? 32 : 24} />
      </button>
      <button
        onClick={togglePlay}
        className={cn(
          "rounded-full bg-primary text-black flex items-center justify-center hover:scale-105 transition-all shadow-[0_0_15px_hsl(var(--primary)/0.5)]",
          isExpanded ? "w-16 h-16" : "w-10 h-10 md:w-10 md:h-10 shrink-0"
        )}
        aria-label={isPlaying ? "Pause" : "Play"}
      >
        {isPlaying ? (
          <Pause size={isExpanded ? 32 : 20} fill="currentColor" />
        ) : (
          <Play size={isExpanded ? 32 : 20} fill="currentColor" className="ml-1" />
        )}
      </button>
      <button
        onClick={nextTrack}
        className={cn(
          "text-gray-400 hover:text-white transition-colors hover:scale-110 active:scale-95",
          !isExpanded && "hidden md:block"
        )}
        aria-label="Next track"
      >
        <SkipForward size={isExpanded ? 32 : 24} />
      </button>
    </div>
  );
}
