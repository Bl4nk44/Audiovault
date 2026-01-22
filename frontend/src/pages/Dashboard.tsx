import { motion } from "framer-motion";
import {
  ArrowRight,
  Clock,
  Download,
  HardDrive,
  List,
  Music,
  Search,
  Settings,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "../hooks/useTranslation";
import api from "../services/api";

import SystemStats from "../components/dashboard/SystemStats";
import { GlassCard } from "../components/ui/GlassCard";

interface ActiveDownloadItem {
  id: string;
  title: string;
  artist: string;
  status: string;
  progress: number;
  image_url?: string;
}

interface DashboardStats {
  total_downloads: string;
  tracks_in_library: string;
  pending_queue: string;
  storage_free: string;
  active_download: ActiveDownloadItem | null;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const navigate = useNavigate();

  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState("");
  const [dashboardStats, setDashboardStats] = useState<DashboardStats>({
    total_downloads: "-",
    tracks_in_library: "-",
    pending_queue: "-",
    storage_free: "-",
    active_download: null,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get("/dashboard/stats");
        setDashboardStats((prev) => {
          const newData = response.data;
          // Preserve local progress if ID matches
          if (
            prev.active_download &&
            newData.active_download &&
            prev.active_download.id === newData.active_download.id
          ) {
            newData.active_download.progress = Math.max(
              prev.active_download.progress,
              newData.active_download.progress
            );
          }
          return newData;
        });
      } catch (error) {
        console.error("Failed to fetch dashboard stats", error);
      }
    };
    fetchStats();
    // Poll for updates every 5 seconds (fallback and for other stats)
    const interval = setInterval(fetchStats, 5000);

    // WebSocket listeners for real-time progress
    // WebSocket listeners for real-time progress
    const handleProgress = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      console.log("Dashboard received download:progress", detail);
      const { download_id, progress, status, track } = detail;
      setDashboardStats((prev) => {
        // If we have track info, we can construct/update the active download immediately
        if (track) {
          return {
            ...prev,
            active_download: {
              id: download_id,
              title: track.title,
              artist: track.artist,
              image_url: track.image_url,
              status: status,
              progress: progress,
            },
          };
        }

        // Fallback for legacy events (shouldn't happen with new backend)
        if (prev.active_download && prev.active_download.id === download_id) {
          return {
            ...prev,
            active_download: {
              ...prev.active_download,
              progress: progress,
              status: status,
            },
          };
        }

        // If we don't have track info and it's a new download, we must fetch
        if (!prev.active_download || prev.active_download.id !== download_id) {
          fetchStats();
          return prev;
        }
        return prev;
      });
    };

    const handleCompleted = () => {
      // Refresh stats to show next download or empty state
      fetchStats();
    };

    globalThis.addEventListener("download:progress", handleProgress);
    globalThis.addEventListener("download:completed", handleCompleted);

    return () => {
      clearInterval(interval);
      globalThis.removeEventListener("download:progress", handleProgress);
      globalThis.removeEventListener("download:completed", handleCompleted);
    };
  }, []);

  const stats = [
    {
      label: t("dashboard.stats.totalDownloads"),
      value: dashboardStats.total_downloads,
      icon: Download,
      color: "text-blue-400",
      gradient: "from-blue-500/20 to-blue-600/5",
      depth: "border-b-blue-500/20",
    },
    {
      label: t("dashboard.stats.tracksLibrary"),
      value: dashboardStats.tracks_in_library,
      icon: Music,
      color: "text-green-400",
      gradient: "from-green-500/20 to-green-600/5",
      depth: "border-b-green-500/20",
    },
    {
      label: t("dashboard.stats.pendingQueue"),
      value: dashboardStats.pending_queue,
      icon: Clock,
      color: "text-orange-400",
      gradient: "from-orange-500/20 to-orange-600/5",
      depth: "border-b-orange-500/20",
    },
    {
      label: t("dashboard.stats.storageFree"),
      value: dashboardStats.storage_free,
      icon: HardDrive,
      color: "text-purple-400",
      gradient: "from-purple-500/20 to-purple-600/5",
      depth: "border-b-purple-500/20",
    },
  ];

  return (
    <div className="relative min-h-screen">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative z-10 space-y-8 p-6 max-w-7xl mx-auto"
      >
        {/* Header Section */}
        <motion.div
          variants={item}
          className="flex flex-col md:flex-row justify-between items-end gap-4"
        >
          <div>
            <h2 className="text-4xl font-bold tracking-tight text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.4)]">
              {t("dashboard.title")}
            </h2>
            <p className="text-gray-400 mt-2 text-lg">{t("dashboard.subtitle")}</p>
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div variants={container} className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <GlassCard
              key={stat.label}
              variant="interactive"
              variants={item}
              whileHover={{ y: -5 }}
              className={`p-6 border-b-[6px] ${stat.depth} bg-linear-to-br ${stat.gradient} relative overflow-hidden group`}
            >
              <div className="absolute top-1/2 right-6 -translate-y-1/2 opacity-10 group-hover:opacity-20 transition-all transform group-hover:scale-110 duration-500">
                <stat.icon size={80} />
              </div>

              <div className="flex items-center justify-between space-y-0 pb-4 relative z-10">
                <p className="text-sm font-medium text-gray-300">{stat.label}</p>
              </div>
              <div className="text-4xl font-bold text-white relative z-10 drop-shadow-md">
                {stat.value}
              </div>
            </GlassCard>
          ))}
        </motion.div>

        {/* Hero Input Section */}
        <motion.div variants={item} className="relative z-20">
          <div className="relative group rounded-2xl">
            <div className="absolute -inset-0.5 bg-linear-to-r from-primary to-purple-600 rounded-2xl blur opacity-30 group-hover:opacity-60 transition duration-500"></div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (searchQuery.trim()) {
                  navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
                }
              }}
              className="relative bg-black/40 rounded-2xl p-2 flex items-center border border-white/10 backdrop-blur-xl"
            >
              <Search className="ml-4 text-gray-400" size={24} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("dashboard.searchPlaceholder")}
                className="w-full bg-transparent border-none text-white text-lg placeholder:text-gray-500 px-4 py-4 focus:outline-none focus:ring-0"
              />
              <motion.button
                type="submit"
                disabled={!searchQuery.trim()}
                whileHover={{ y: -1 }}
                whileTap={{
                  y: 2,
                  borderBottomWidth: "0px",
                  marginBottom: "2px",
                }}
                className="bg-primary hover:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed text-black font-bold p-3 rounded-xl transition-all border-b-4 border-black/20"
              >
                <ArrowRight size={24} />
              </motion.button>
            </form>
          </div>
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          {/* Server Stats (Left Column, 2 spans) */}
          <motion.div variants={item} className="lg:col-span-2 flex flex-col">
            <SystemStats />
          </motion.div>

          {/* Quick Links Grid (Right Column, 1 span) */}
          <motion.div variants={item} className="flex flex-col">
            <div className="grid grid-cols-2 gap-4 h-full">
              {[
                {
                  label: t("dashboard.quickLinks.library"),
                  icon: Music,
                  color: "text-green-400",
                  bg: "bg-green-500/10 hover:bg-green-500/20",
                  border: "border-green-500/20",
                  depth: "border-b-green-900/50",
                  path: "/library",
                },
                {
                  label: t("dashboard.quickLinks.watchlist"),
                  icon: Clock,
                  color: "text-orange-400",
                  bg: "bg-orange-500/10 hover:bg-orange-500/20",
                  border: "border-orange-500/20",
                  depth: "border-b-orange-900/50",
                  path: "/watchlist",
                },
                {
                  label: t("dashboard.quickLinks.queue"),
                  icon: List,
                  color: "text-blue-400",
                  bg: "bg-blue-500/10 hover:bg-blue-500/20",
                  border: "border-blue-500/20",
                  depth: "border-b-blue-900/50",
                  path: "/queue",
                },
                {
                  label: t("dashboard.quickLinks.settings"),
                  icon: Settings,
                  color: "text-gray-400",
                  bg: "bg-white/5 hover:bg-white/10",
                  border: "border-white/10",
                  depth: "border-b-white/10",
                  path: "/settings",
                },
              ].map((link) => (
                <motion.button
                  key={link.label}
                  whileHover={{ y: -2 }}
                  whileTap={{
                    y: 4,
                    borderBottomWidth: "0px",
                    marginBottom: "4px",
                  }}
                  transition={{ type: "spring", stiffness: 400, damping: 15 }}
                  onClick={() => navigate(link.path)}
                  className={`flex flex-col items-center justify-center p-4 rounded-3xl border border-b-[6px] ${link.border} ${link.depth} ${link.bg} transition-colors gap-3 w-full h-full min-h-47.5 backdrop-blur-sm cursor-pointer`}
                >
                  <div className={`p-4 rounded-full bg-black/20 ${link.color} shadow-lg`}>
                    <link.icon size={32} />
                  </div>
                  <span className="text-white font-bold text-lg">{link.label}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
