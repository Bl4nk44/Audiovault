import {
  Home,
  Search,
  Settings as SettingsIcon,
  Eye,
  Music,
  Download,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";
import { motion } from "framer-motion";
import { useTranslation } from "../../hooks/useTranslation";
import Logo from "./Logo";

export default function Sidebar() {
  const { t } = useTranslation();

  const navItems = [
    { icon: Home, label: t("sidebar.home"), path: "/" },
    { icon: Search, label: t("sidebar.search"), path: "/search" },
    { icon: Eye, label: t("sidebar.watchlist"), path: "/watchlist" },
    { icon: Music, label: t("sidebar.library"), path: "/library" },
    { icon: Download, label: t("sidebar.downloads"), path: "/queue" },
    { icon: SettingsIcon, label: t("sidebar.settings"), path: "/settings" },
  ];

  return (
    <motion.aside
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="w-full h-full flex flex-col gap-4 z-30"
    >
      <aside className="w-64 bg-black/40 backdrop-blur-xl h-screen border-r border-white/5 fixed left-0 top-0 z-50 rounded-(--radius) p-6 flex flex-col gap-6 shadow-2xl">
        <motion.div
          whileHover={{ scale: 1.02 }}
          className="cursor-default px-2"
        >
          <Logo />
        </motion.div>

        <nav className="flex flex-col gap-2">
          {navItems.map((navItem) => (
            <NavLink
              key={navItem.path}
              to={navItem.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-4 text-base font-bold transition-all duration-300 px-4 py-3.5 rounded-xl group relative overflow-hidden",
                  isActive
                    ? "text-white bg-white/10 shadow-[0_0_15px_rgba(255,255,255,0.05)] border border-white/5"
                    : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="activeNav"
                      className="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-primary rounded-r-full shadow-[0_0_10px_rgba(34,197,94,0.8)]"
                    />
                  )}
                  <navItem.icon
                    size={24}
                    className={cn(
                      "transition-transform duration-300 group-hover:scale-110",
                      isActive &&
                        "text-primary drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]"
                    )}
                  />
                  <span className="relative z-10">{navItem.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </aside>
    </motion.aside>
  );
}
