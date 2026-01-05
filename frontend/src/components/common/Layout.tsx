import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Navbar from "./Navbar";
import Player from "../player/Player";
import DownloadNotifications from "./DownloadNotifications";

export default function Layout() {
  return (
    <div className="flex h-screen text-foreground overflow-hidden p-3 gap-3 relative group">
      <div className="w-72 h-full shrink-0 z-30">
        <Sidebar />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden glass-neon rounded-3xl relative z-10 transition-[background-color,backdrop-filter] duration-500">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6 scroll-smooth custom-scrollbar pb-24">
          <Outlet />
        </main>
        <Player />
        <DownloadNotifications />
      </div>
    </div>
  );
}
