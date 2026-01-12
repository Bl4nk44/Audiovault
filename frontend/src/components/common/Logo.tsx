import { cn } from "../../lib/utils";

interface LogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
}

export default function Logo({
  className,
  size = "md",
  showText = true,
}: Readonly<LogoProps>) {
  const sizeClasses = {
    sm: "w-8 h-8",
    md: "w-12 h-12",
    lg: "w-20 h-20",
    xl: "w-32 h-32",
  };

  const textSizeClasses = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-4xl",
    xl: "text-5xl",
  };

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative">
        <div
          className={cn("absolute inset-0 bg-primary/50 blur-lg rounded-full")}
        />
        <div
          className={cn(
            "rounded-xl bg-linear-to-r from-primary to-green-400 flex items-center justify-center shadow-[0_0_15px_rgba(34,197,94,0.3)] group-hover:shadow-[0_0_25px_rgba(34,197,94,0.5)] transition-all duration-300 relative z-10",
            sizeClasses[size]
          )}
        >
          <img
            src="/logo.png"
            alt="Audiovault"
            className="w-full h-full object-contain p-0.5"
          />
        </div>
      </div>
      {showText && (
        <span
          className={cn(
            "font-bold text-white tracking-tight",
            textSizeClasses[size]
          )}
        >
          Audiovault
        </span>
      )}
    </div>
  );
}
