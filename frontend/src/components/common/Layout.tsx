import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import Player from "../player/Player";
import DownloadNotifications from "./DownloadNotifications";
<<<<<<< HEAD
import MobileNav from "./MobileNav";
=======
import { useEffect } from "react";
import api from "../../services/api";
import toast from "react-hot-toast";
>>>>>>> temp/release-prep

export default function Layout() {
  const isDev = import.meta.env.DEV;

  useEffect(() => {
    const checkUpdates = async () => {
      try {
        const { data } = await api.get("/system/check-update");
        if (data.update_available) {
          toast(
            (t) => (
              <div className="flex flex-col gap-2">
                <span className="font-bold">New Version Available! 🚀</span>
                <span className="text-sm">
                  Version {data.latest_version} is now available.
                </span>
                <div className="flex gap-2 mt-1">
                  <a
                    href={data.release_url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1 bg-primary text-black rounded-lg text-xs font-bold hover:opacity-90"
                    onClick={() => toast.dismiss(t.id)}
                  >
                    View Release
                  </a>
                  <button
                    onClick={() => toast.dismiss(t.id)}
                    className="px-3 py-1 bg-white/10 rounded-lg text-xs hover:bg-white/20"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ),
            {
              duration: 10000,
              icon: "🎉",
            }
          );
        }
      } catch (error) {
        console.error("Failed to check for updates:", error);
      }
    };

    checkUpdates();
  }, []);

  return (
<<<<<<< HEAD
    <div className="flex h-screen text-foreground overflow-hidden p-0 md:p-3 gap-0 md:gap-3 relative group bg-background">
      {/* Sidebar - Desktop Only */}
      <div className="hidden md:block w-72 h-full shrink-0 z-30">
=======
    <div className="flex h-screen text-foreground overflow-hidden p-3 gap-3 relative group">
      {isDev && (
        <div className="fixed bottom-4 right-4 z-[100] bg-orange-500 text-black px-3 py-1 rounded-full text-xs font-black tracking-wider shadow-lg pointer-events-none animate-pulse">
          DEV BUILD
        </div>
      )}
      <div className="w-72 h-full shrink-0 z-30">
>>>>>>> temp/release-prep
        <Sidebar />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden glass-neon rounded-none md:rounded-3xl relative z-10 transition-[background-color,backdrop-filter] duration-500 w-full">
        <div className="md:px-6 md:pt-4 px-4 pt-2">
          <Navbar />
        </div>

        <main className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth custom-scrollbar pb-32 md:pb-24">
          <Outlet />
        </main>

        {/* Player - visible above nav on mobile */}
        <div className="z-20 relative bg-background/50 md:bg-transparent backdrop-blur-md md:backdrop-blur-none border-t border-white/5 md:border-none">
          <Player />
        </div>

        <DownloadNotifications />
      </div>

      {/* Mobile Navigation - Mobile Only */}
      <MobileNav />
    </div>
  );
}
