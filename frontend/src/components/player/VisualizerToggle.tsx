import { Activity } from "lucide-react";
import { cn } from "../../lib/utils";

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
  return (
    <button
      onClick={() => setShowVisualizer(!showVisualizer)}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-full transition-all text-sm font-medium",
        showVisualizer
          ? "text-primary bg-primary/10 border border-primary/20 shadow-[0_0_10px_hsl(var(--primary)/0.2)]"
          : "text-gray-400 bg-white/5 border border-white/5 hover:bg-white/10 hover:text-white",
        !isExpanded && "hidden md:flex"
      )}
      title="Toggle Visualizer"
      style={{
        display: /iPhone|iPad|iPod/i.test(navigator.userAgent) ? "none" : "flex",
      }}
    >
      <Activity size={16} />
      <span>Visualizer</span>
    </button>
  );
}
