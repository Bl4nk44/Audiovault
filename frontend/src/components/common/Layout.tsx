import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import Player from "../player/Player";
import DownloadNotifications from "./DownloadNotifications";
import MobileNav from "./MobileNav";
import { useEffect, useRef } from "react";
import api from "../../services/api";
import { useSocketEvents } from "../../hooks/useSocketEvents";
import { useStore } from "../../store/useStore";

export default function Layout() {
  const isDev = import.meta.env.DEV;
  const { addNotification } = useStore();

  // Initialize socket connection for real-time download progress
  useSocketEvents();

  const hasChecked = useRef(false);

  useEffect(() => {
    if (hasChecked.current) return;
    hasChecked.current = true;

    const checkUpdates = async () => {
      try {
        const { data } = await api.get("/system/check-update");
        if (data.update_available) {
          const message = isDev
            ? "New commits on dev branch."
            : `Version ${data.latest_version} is available.`;
          addNotification("info", message);
        }
      } catch (error) {
        console.error("Failed to check for updates:", error);
      }
    };

    checkUpdates();
  }, [isDev, addNotification]);

  return (
    <div className="flex h-screen text-foreground overflow-hidden p-0 md:p-3 gap-0 md:gap-3 relative group bg-background">
      {isDev && (
        <div className="fixed bottom-4 right-4 z-100 bg-orange-500 text-black px-3 py-1 rounded-full text-xs font-black tracking-wider shadow-lg pointer-events-none animate-pulse">
          DEV BUILD
        </div>
      )}
      {/* Sidebar - Desktop Only */}
      <div className="hidden md:block w-72 h-full shrink-0 z-30">
        <Sidebar />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden glass-neon rounded-none md:rounded-3xl relative z-10 transition-[background-color,backdrop-filter] duration-500 w-full">
        <div className="md:px-6 md:pt-4 px-4 pt-2">
          <Navbar />
        </div>

        <main className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth custom-scrollbar pb-40 md:pb-32">
          <Outlet />
        </main>

        {/* Player - visible above nav on mobile */}
        <div className="z-20 relative">
          <Player />
        </div>

        <DownloadNotifications />
      </div>

      {/* Mobile Navigation - Mobile Only */}
      <MobileNav />
    </div>
  );
}
