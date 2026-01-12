import { formatTime } from "../../utils/format";
import { cn } from "../../lib/utils";

interface ProgressBarProps {
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  isExpanded: boolean;
}

export function ProgressBar({
  currentTime,
  duration,
  onSeek,
  isExpanded,
}: Readonly<ProgressBarProps>) {
  return (
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
        onChange={(e) => onSeek(Number(e.target.value))}
        className="flex-1 h-1 bg-white/10 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full hover:[&::-webkit-slider-thumb]:bg-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
        aria-label="Seek slider"
        style={{
          backgroundSize: `${(currentTime / (duration || 1)) * 100}% 100%`,
          backgroundImage: `linear-gradient(to right, hsl(var(--primary)) 0%, hsl(var(--primary)) 100%)`,
          backgroundRepeat: "no-repeat",
        }}
      />
      <span>{formatTime(duration)}</span>
    </div>
  );
}
