import { Activity, Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "../../lib/utils";
import { type VisualizerMode } from "../../store/slices/playerSlice";
import { useStore } from "../../store/useStore";

interface VisualizerToggleProps {
  showVisualizer: boolean;
  setShowVisualizer: (show: boolean) => void;
  isExpanded: boolean;
}

export function VisualizerToggle({
  showVisualizer,
  setShowVisualizer,
  isExpanded,
}: Readonly<VisualizerToggleProps>) {
  const { visualizerMode, setVisualizerMode } = useStore();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const modes: { id: VisualizerMode; label: string }[] = [
    { id: "classic", label: "Classic Bars" },
    { id: "wave", label: "Waveform" },
    { id: "circle", label: "Radial Circle" },
    { id: "particles", label: "Particles" },
    { id: "glow", label: "Ambient Glow" },
  ];

  return (
    <div className="relative" ref={menuRef}>
      <div
        className={cn(
          "flex items-center rounded-full border transition-all",
          showVisualizer
            ? "border-primary/20 bg-primary/10 shadow-[0_0_10px_hsl(var(--primary)/0.2)]"
            : "border-white/5 bg-white/5 hover:bg-white/10"
        )}
      >
        <button
          onClick={() => setShowVisualizer(!showVisualizer)}
          className={cn(
            "flex items-center gap-2 pl-3 pr-2 py-1.5 text-sm font-medium transition-colors rounded-l-full",
            showVisualizer ? "text-primary" : "text-gray-400 hover:text-white"
          )}
          title="Toggle Visualizer"
        >
          <Activity size={16} />
          <span className={cn(!isExpanded && "hidden md:flex")}>Visualizer</span>
        </button>

        <div
          className={cn("w-px h-4 mx-0", showVisualizer ? "bg-primary/20" : "bg-white/10")}
        ></div>

        <button
          onClick={() => setShowMenu(!showMenu)}
          className={cn(
            "pl-1 pr-2 py-1.5 rounded-r-full transition-colors",
            showVisualizer
              ? "text-primary hover:bg-primary/20"
              : "text-gray-400 hover:text-white hover:bg-white/10"
          )}
        >
          <ChevronDown
            size={14}
            className={cn("transition-transform duration-200", showMenu && "rotate-180")}
          />
        </button>
      </div>

      {/* Dropdown Menu */}
      {showMenu && (
        <div className="absolute bottom-full mb-3 right-0 w-48 bg-black/90 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl overflow-hidden py-1 z-50 animate-in fade-in slide-in-from-bottom-2">
          <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Visualizer Style
          </div>
          {modes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => {
                setVisualizerMode(mode.id);
                if (!showVisualizer) setShowVisualizer(true);
                setShowMenu(false);
              }}
              className="w-full text-left px-4 py-2.5 text-sm flex items-center justify-between hover:bg-white/10 transition-colors group"
            >
              <span
                className={cn(
                  "transition-colors",
                  visualizerMode === mode.id
                    ? "text-primary font-medium"
                    : "text-gray-300 group-hover:text-white"
                )}
              >
                {mode.label}
              </span>
              {visualizerMode === mode.id && <Check size={14} className="text-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
