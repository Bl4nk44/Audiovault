import { Volume2, VolumeX } from "lucide-react";
import { cn } from "../../lib/utils";

interface VolumeControlProps {
  volume: number;
  setVolume: (vol: number) => void;
  isExpanded: boolean;
}

export function VolumeControl({ volume, setVolume, isExpanded }: Readonly<VolumeControlProps>) {
  return (
    <div className={cn("flex items-center gap-2 group", !isExpanded && "hidden md:flex")}>
      <button
        onClick={() => setVolume(volume === 0 ? 1 : 0)}
        className="text-gray-400 hover:text-white"
        aria-label={volume === 0 ? "Unmute" : "Mute"}
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
  );
}
