import { forwardRef } from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "../../lib/utils";
import { Loader2 } from "lucide-react";

interface ButtonProps extends Omit<HTMLMotionProps<"button">, "children"> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
  children: React.ReactNode;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      children,
      ...props
    },
    ref
  ) => {
    const variants = {
      primary:
        "bg-primary/80 backdrop-blur-md text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_rgba(34,197,94,0.3)] hover:shadow-[0_0_30px_rgba(34,197,94,0.5)] border border-white/10 relative overflow-hidden group",
      secondary:
        "bg-secondary/50 backdrop-blur-sm text-secondary-foreground hover:bg-secondary/70 border border-white/5",
      outline:
        "bg-transparent border-border text-foreground hover:bg-white/5 hover:text-accent-foreground backdrop-blur-sm",
      ghost:
        "bg-transparent text-muted-foreground hover:text-foreground hover:bg-white/5 border-transparent",
      danger:
        "bg-destructive/80 text-destructive-foreground hover:bg-destructive/90 border-transparent shadow-[0_0_15px_rgba(239,68,68,0.4)]",
    };

    const sizes = {
      sm: "h-8 px-3 text-xs",
      md: "h-10 px-6 text-sm",
      lg: "h-12 px-8 text-base",
      icon: "h-10 w-10 p-2 flex items-center justify-center",
    };

    return (
      <motion.button
        ref={ref}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        disabled={isLoading || props.disabled}
        className={cn(
          "relative inline-flex items-center justify-center rounded-full font-bold transition-all duration-300 border focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background disabled:opacity-50 disabled:pointer-events-none active:scale-95",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {/* Shine Effect for Primary Variant */}
        {variant === "primary" && (
          <div className="absolute inset-0 -translate-x-full group-hover:animate-[shine_1.5s_ease-in-out_infinite] z-0 pointer-events-none">
            <div className="w-1/2 h-full bg-linear-to-r from-transparent via-white/20 to-transparent skew-x-[-20deg]" />
          </div>
        )}

        <span className="relative z-10 flex items-center justify-center gap-2">
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {children}
        </span>
      </motion.button>
    );
  }
);

Button.displayName = "Button";

export default Button;
