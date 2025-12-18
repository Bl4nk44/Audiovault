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
        "bg-primary text-primary-foreground hover:brightness-110 shadow-[0_0_15px_rgba(34,197,94,0.3)] hover:shadow-[0_0_25px_rgba(34,197,94,0.5)] border-transparent",
      secondary:
        "bg-secondary text-secondary-foreground hover:brightness-110 border-transparent",
      outline:
        "bg-transparent border-border text-foreground hover:bg-accent hover:text-accent-foreground",
      ghost:
        "bg-transparent text-muted-foreground hover:text-foreground hover:bg-accent border-transparent",
      danger:
        "bg-destructive text-destructive-foreground hover:brightness-110 border-transparent",
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
          "relative inline-flex items-center justify-center rounded-full font-bold transition-all duration-300 border focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background disabled:opacity-50 disabled:pointer-events-none",
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </motion.button>
    );
  }
);

Button.displayName = "Button";

export default Button;
