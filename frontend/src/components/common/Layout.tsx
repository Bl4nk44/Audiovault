import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import Player from "../player/Player";
import DownloadNotifications from "./DownloadNotifications";
import MobileNav from "./MobileNav";

export default function Layout() {
  return (
    <div className="flex h-screen text-foreground overflow-hidden p-0 md:p-3 gap-0 md:gap-3 relative group bg-background">
      {/* Sidebar - Desktop Only */}
      <div className="hidden md:block w-72 h-full shrink-0 z-30">
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
