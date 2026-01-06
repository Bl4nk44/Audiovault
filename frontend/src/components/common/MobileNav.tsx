import { Home, Search, Music, Download, Settings, Menu } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";
import { motion } from "framer-motion";

export default function MobileNav() {
  const navItems = [
    { icon: Home, label: "Home", path: "/" },
    { icon: Search, label: "Search", path: "/search" },
    { icon: Music, label: "Library", path: "/library" },
    { icon: Download, label: "Queue", path: "/queue" },
    { icon: Settings, label: "Settings", path: "/settings" },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden pb-safe">
      <div className="glass-neon border-t border-white/5 px-6 py-3 flex justify-between items-center backdrop-blur-xl bg-background/80">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center justify-center gap-1 p-2 rounded-xl transition-all relative overflow-hidden",
                isActive
                  ? "text-primary"
                  : "text-muted-foreground hover:text-white"
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId="mobileNavActive"
                    className="absolute inset-0 bg-primary/10 rounded-xl"
                    initial={false}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  />
                )}
                <item.icon
                  size={24}
                  className={cn(
                    isActive && "drop-shadow-[0_0_8px_rgba(var(--primary),0.5)]"
                  )}
                />
                <span className="text-[10px] font-medium">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
