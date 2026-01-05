import { cn } from "../../lib/utils";
import { motion, type HTMLMotionProps } from "framer-motion";

interface GlassCardProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "interactive" | "flat";
  intensity?: "low" | "medium" | "high";
}

export const GlassCard = ({
  children,
  className,
  variant = "default",
  intensity = "medium",
  ...props
}: GlassCardProps) => {
  const intensityMap = {
    low: "bg-background/20 backdrop-blur-sm",
    medium: "bg-background/30 backdrop-blur-md",
    high: "bg-background/40 backdrop-blur-xl",
  };

  const variants = {
    default: "border border-white/5",
    interactive:
      "border border-white/5 hover:bg-background/40 hover:border-white/10 transition-all duration-300 cursor-pointer hover:shadow-[0_0_20px_rgba(255,255,255,0.05)]",
    flat: "border-none shadow-none",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "rounded-2xl relative overflow-hidden",
        intensityMap[intensity],
        variants[variant],
        className
      )}
      {...props}
    >
      {/* Glossy gradient overlay */}
      <div className="absolute inset-0 bg-linear-to-br from-white/5 to-transparent pointer-events-none" />

      <div className="relative z-10">{children}</div>
    </motion.div>
  );
};
