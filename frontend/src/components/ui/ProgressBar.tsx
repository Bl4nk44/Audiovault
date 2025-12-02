import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

interface ProgressBarProps {
    progress: number
    className?: string
    showLabel?: boolean
    height?: string
    color?: string
}

export default function ProgressBar({
    progress,
    className,
    showLabel = false,
    height = "h-1.5",
    color = "bg-primary"
}: ProgressBarProps) {
    // Ensure progress is between 0 and 100
    const clampedProgress = Math.min(Math.max(progress, 0), 100)

    return (
        <div className={cn("w-full flex flex-col gap-1", className)}>
            <div className={cn("w-full bg-white/10 rounded-full overflow-hidden backdrop-blur-sm", height)}>
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${clampedProgress}%` }}
                    transition={{ type: "spring", stiffness: 50, damping: 15 }}
                    className={cn(
                        "h-full rounded-full relative overflow-hidden",
                        color
                    )}
                >
                    {/* Animated shimmer effect */}
                    <motion.div
                        className="absolute top-0 left-0 bottom-0 w-full bg-gradient-to-r from-transparent via-white/30 to-transparent"
                        initial={{ x: "-100%" }}
                        animate={{ x: "100%" }}
                        transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                    />
                </motion.div>
            </div>
            {showLabel && (
                <div className="flex justify-between text-xs text-muted-foreground font-medium">
                    <span>{Math.round(clampedProgress)}%</span>
                </div>
            )}
        </div>
    )
}
