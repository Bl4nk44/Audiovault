import {
  Download,
  Music,
  Clock,
  HardDrive,
  Play,
  Search,
  ArrowRight,
  Settings,
  List,
} from "lucide-react";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import api from "../services/api";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "../hooks/useTranslation";

interface RecentActivityItem {
  id: string;
  track_id?: string;
  title: string;
  artist: string;
  time_ago: string;
  progress: number;
  image_url?: string;
  filename?: string;
}

import { useStore } from "../store/useStore";

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
  recent_activity: RecentActivityItem[];
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
  const { playTrack } = useStore();
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState("");
  const [dashboardStats, setDashboardStats] = useState<DashboardStats>({
    total_downloads: "-",
    tracks_in_library: "-",
    pending_queue: "-",
    storage_free: "-",
    recent_activity: [],
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

    window.addEventListener("download:progress", handleProgress);
    window.addEventListener("download:completed", handleCompleted);

    return () => {
      clearInterval(interval);
      window.removeEventListener("download:progress", handleProgress);
      window.removeEventListener("download:completed", handleCompleted);
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
            <p className="text-gray-400 mt-2 text-lg">
              {t("dashboard.subtitle")}
            </p>
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div
          variants={container}
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-4"
        >
          {stats.map((stat) => (
            <motion.div
              key={stat.label}
              variants={item}
              whileHover={{ y: -5 }}
              className={`p-6 rounded-3xl border border-white/10 border-b-[6px] ${stat.depth} bg-linear-to-br ${stat.gradient} backdrop-blur-xl shadow-xl relative overflow-hidden group`}
            >
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500">
                <stat.icon size={100} />
              </div>

              <div className="flex items-center justify-between space-y-0 pb-4 relative z-10">
                <p className="text-sm font-medium text-gray-300">
                  {stat.label}
                </p>
              </div>
              <div className="text-4xl font-bold text-white relative z-10 drop-shadow-md">
                {stat.value}
              </div>
            </motion.div>
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
                placeholder="Paste URL (YouTube, Spotify...) or search for music..."
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
          {/* Recent Activity (Left Column, 2 spans) */}
          <motion.div variants={item} className="lg:col-span-2 flex flex-col">
            <div className="rounded-3xl border border-white/10 bg-black/20 backdrop-blur-xl p-8 shadow-2xl flex-1 flex flex-col justify-between min-h-[420px]">
              <div>
                <h3 className="font-bold mb-6 text-2xl text-white flex items-center gap-3">
                  <span className="w-1.5 h-8 bg-primary rounded-full shadow-[0_0_10px_rgba(var(--primary-rgb),0.5)] shadow-primary/50"></span>
                  {t("dashboard.recentActivity")}
                </h3>
                <div className="space-y-3">
                  {dashboardStats.recent_activity.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-12 text-gray-400">
                      <Music size={48} className="mb-4 opacity-20" />
                      <p className="text-lg">{t("dashboard.noActivity")}</p>
                    </div>
                  ) : (
                    dashboardStats.recent_activity
                      .slice(0, 3)
                      .map((activity: RecentActivityItem) => (
                        <motion.div
                          key={activity.id}
                          whileHover={{
                            y: -2,
                          }}
                          whileTap={{
                            y: 2,
                            borderBottomWidth: "0px",
                            marginBottom: "2px",
                          }}
                          onClick={() => {
                            const currentTrack =
                              useStore.getState().currentTrack;
                            const isCurrent =
                              (activity.track_id &&
                                currentTrack?.id === activity.track_id) ||
                              currentTrack?.id === activity.id;

                            if (isCurrent && useStore.getState().isPlaying) {
                              useStore.getState().togglePlay();
                            } else {
                              playTrack(
                                {
                                  id: activity.track_id || activity.id,
                                  title: activity.title,
                                  artist: activity.artist,
                                  cover: activity.image_url,
                                  source: "local",
                                  filename: activity.filename,
                                  album: "Recent Activity",
                                },
                                dashboardStats.recent_activity.map((a) => ({
                                  id: a.track_id || a.id,
                                  title: a.title,
                                  artist: a.artist,
                                  cover: a.image_url,
                                  source: "local",
                                  filename: a.filename,
                                  album: "Recent Activity",
                                }))
                              );
                            }
                          }}
                          className="flex items-center gap-4 p-3 rounded-2xl bg-white/5 border-b-4 border-white/5 transition-all group cursor-pointer border-t border-r border-l hover:border-white/10 hover:bg-white/10"
                        >
                          <div className="w-12 h-12 rounded-xl bg-linear-to-br from-primary to-primary/60 flex items-center justify-center shadow-lg shadow-primary/20 group-hover:scale-110 transition-transform duration-300 relative overflow-hidden shrink-0">
                            {activity.image_url ? (
                              <img
                                src={activity.image_url}
                                alt={activity.title}
                                className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                              />
                            ) : (
                              <Music size={24} className="text-black/50" />
                            )}
                            <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity backdrop-blur-[1px] z-10">
                              <Play
                                size={20}
                                className="text-white fill-white drop-shadow-md"
                              />
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-center mb-0.5">
                              <p className="font-bold text-base text-white group-hover:text-primary transition-colors truncate pr-2">
                                {activity.title}
                              </p>
                              <span className="text-[10px] text-gray-500 bg-black/40 px-1.5 py-0.5 rounded-md border border-white/5 whitespace-nowrap">
                                {activity.time_ago}
                              </span>
                            </div>
                            <p className="text-xs text-gray-400 truncate font-medium">
                              {activity.artist}
                            </p>
                          </div>
                        </motion.div>
                      ))
                  )}
                </div>
              </div>
            </div>
          </motion.div>

          {/* Quick Links Grid (Right Column, 1 span) */}
          <motion.div variants={item} className="flex flex-col">
            <div className="grid grid-cols-2 gap-4 h-full">
              {[
                {
                  label: "Library",
                  icon: Music,
                  color: "text-green-400",
                  bg: "bg-green-500/10 hover:bg-green-500/20",
                  border: "border-green-500/20",
                  depth: "border-b-green-900/50",
                  path: "/library",
                },
                {
                  label: "Watchlist",
                  icon: Clock,
                  color: "text-orange-400",
                  bg: "bg-orange-500/10 hover:bg-orange-500/20",
                  border: "border-orange-500/20",
                  depth: "border-b-orange-900/50",
                  path: "/watchlist",
                },
                {
                  label: "Queue",
                  icon: List,
                  color: "text-blue-400",
                  bg: "bg-blue-500/10 hover:bg-blue-500/20",
                  border: "border-blue-500/20",
                  depth: "border-b-blue-900/50",
                  path: "/queue",
                },
                {
                  label: "Settings",
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
                  className={`flex flex-col items-center justify-center p-4 rounded-3xl border border-b-[6px] ${link.border} ${link.depth} ${link.bg} transition-colors gap-3 w-full h-full min-h-[190px] backdrop-blur-sm cursor-pointer`}
                >
                  <div
                    className={`p-4 rounded-full bg-black/20 ${link.color} shadow-lg`}
                  >
                    <link.icon size={32} />
                  </div>
                  <span className="text-white font-bold text-lg">
                    {link.label}
                  </span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Active Download - Full Width Bottom Section */}
        {dashboardStats.active_download && (
          <motion.div variants={item} className="mt-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-3xl border border-primary/30 border-b-[6px] border-b-primary/30 bg-linear-to-b from-black/80 to-black/60 backdrop-blur-xl p-8 shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] shadow-primary/20 relative overflow-hidden group flex flex-col justify-center"
            >
              {/* Background Image Blur Effect */}
              {dashboardStats.active_download.image_url && (
                <div
                  className="absolute inset-0 opacity-20 bg-cover bg-center blur-2xl pointer-events-none"
                  style={{
                    backgroundImage: `url(${dashboardStats.active_download.image_url})`,
                  }}
                />
              )}

              <div className="flex flex-col md:flex-row items-center gap-8 relative z-10">
                {/* Album Art */}
                <div className="relative shrink-0">
                  {dashboardStats.active_download.image_url ? (
                    <img
                      src={dashboardStats.active_download.image_url}
                      alt="Cover"
                      className="w-24 h-24 rounded-2xl object-cover border border-white/10 shadow-2xl animate-[spin_8s_linear_infinite]"
                    />
                  ) : (
                    <div className="w-24 h-24 rounded-2xl bg-primary/20 text-primary flex items-center justify-center border border-primary/20 animate-pulse shadow-2xl">
                      <Download size={40} />
                    </div>
                  )}
                  {dashboardStats.active_download.status === "downloading" && (
                    <div className="absolute -bottom-2 -right-2 bg-black/60 backdrop-blur-md border border-white/10 rounded-full p-2">
                      <div className="w-3 h-3 bg-primary rounded-full animate-pulse shadow-[0_0_10px_rgba(var(--primary-rgb),1)]"></div>
                    </div>
                  )}
                </div>

                {/* Info & Progress */}
                <div className="flex-1 w-full min-w-0 space-y-5">
                  <div className="flex justify-between items-end">
                    <div>
                      <span className="text-sm text-primary font-bold uppercase tracking-widest mb-1 block">
                        {dashboardStats.active_download.status === "downloading"
                          ? t("dashboard.activeDownload.downloading")
                          : t("dashboard.activeDownload.pending")}
                      </span>
                      <h4 className="text-3xl font-bold text-white truncate leading-tight mb-1">
                        {dashboardStats.active_download.title}
                      </h4>
                      <p className="text-gray-400 text-xl truncate">
                        {dashboardStats.active_download.artist}
                      </p>
                    </div>
                    <div className="text-right hidden md:block">
                      <span className="text-4xl font-bold text-white tabular-nums">
                        {Math.round(dashboardStats.active_download.progress)}%
                      </span>
                    </div>
                  </div>

                  {/* Large Nice Progress Bar */}
                  <div className="h-5 bg-white/10 rounded-full overflow-hidden border border-white/5 relative shadow-inner">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{
                        width: `${dashboardStats.active_download.progress}%`,
                      }}
                      transition={{ ease: "linear" }}
                      className="h-full bg-linear-to-r from-primary via-purple-500 to-primary background-animate bg-size-[200%_auto] shadow-[0_0_20px_rgba(var(--primary-rgb),0.6)] relative"
                    >
                      <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite] transform -skew-x-12"></div>
                    </motion.div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
