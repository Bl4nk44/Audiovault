import { Download, Music, Clock, HardDrive, Play } from "lucide-react";
import { motion } from "framer-motion";
import Button from "../components/ui/Button";
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
    },
    {
      label: t("dashboard.stats.tracksLibrary"),
      value: dashboardStats.tracks_in_library,
      icon: Music,
      color: "text-green-400",
      gradient: "from-green-500/20 to-green-600/5",
    },
    {
      label: t("dashboard.stats.pendingQueue"),
      value: dashboardStats.pending_queue,
      icon: Clock,
      color: "text-orange-400",
      gradient: "from-orange-500/20 to-orange-600/5",
    },
    {
      label: t("dashboard.stats.storageFree"),
      value: dashboardStats.storage_free,
      icon: HardDrive,
      color: "text-purple-400",
      gradient: "from-purple-500/20 to-purple-600/5",
    },
  ];

  return (
    <div className="relative min-h-screen">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="relative z-10 space-y-8 p-6"
      >
        <motion.div variants={item}>
          <h2 className="text-4xl font-bold tracking-tight text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">
            {t("dashboard.title")}
          </h2>
          <p className="text-gray-400 mt-2 text-lg">
            {t("dashboard.subtitle")}
          </p>
        </motion.div>

        <motion.div
          variants={container}
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-4"
        >
          {stats.map((stat) => (
            <motion.div
              key={stat.label}
              variants={item}
              whileHover={{ scale: 1.02, y: -5 }}
              className={`p-6 rounded-3xl border border-white/10 bg-linear-to-br ${stat.gradient} backdrop-blur-xl shadow-xl relative overflow-hidden group`}
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

        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          <motion.div
            variants={item}
            className="col-span-2 rounded-3xl border border-white/10 bg-black/20 backdrop-blur-xl p-8 shadow-2xl space-y-8"
          >
            <div>
              <h3 className="font-bold mb-8 text-2xl text-white flex items-center gap-3">
                <span className="w-1.5 h-8 bg-primary rounded-full shadow-[0_0_10px_rgba(var(--primary-rgb),0.5)] shadow-primary/50"></span>
                {t("dashboard.recentActivity")}
              </h3>
              <div className="space-y-4">
                {dashboardStats.recent_activity.length === 0 ? (
                  <p className="text-gray-400 text-center py-8">
                    {t("dashboard.noActivity")}
                  </p>
                ) : (
                  dashboardStats.recent_activity.map(
                    (activity: RecentActivityItem) => (
                      <motion.div
                        key={activity.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        onClick={() => {
                          // Toggle Logic: Check if currently matching track is playing
                          const currentTrack = useStore.getState().currentTrack;
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
                        className="flex items-center gap-5 p-4 rounded-2xl bg-white/5 hover:bg-white/10 transition-all group cursor-pointer border border-white/5 hover:border-white/10 hover:scale-[1.01]"
                      >
                        <div className="w-12 h-12 rounded-xl bg-linear-to-br from-primary to-primary/60 flex items-center justify-center shadow-lg shadow-primary/20 group-hover:scale-110 transition-transform duration-300 relative overflow-hidden shrink-0">
                          {activity.image_url ? (
                            <img
                              src={activity.image_url}
                              alt={activity.title}
                              className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                            />
                          ) : (
                            <>
                              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity backdrop-blur-[1px] z-10">
                                <Play
                                  size={28}
                                  className="text-white fill-white drop-shadow-md"
                                />
                              </div>
                              <Music
                                size={28}
                                className="text-gray-500 group-hover:opacity-0 transition-opacity"
                              />
                            </>
                          )}
                          {activity.image_url && (
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity backdrop-blur-[1px] z-10">
                              <Play
                                size={28}
                                className="text-white fill-white drop-shadow-md"
                              />
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-bold text-lg text-white group-hover:text-primary transition-colors truncate">
                                {activity.title}
                              </p>
                              <p className="text-sm text-gray-400 truncate font-medium">
                                {activity.artist}
                              </p>
                            </div>
                            <span className="text-xs text-gray-500 bg-white/5 px-2 py-1 rounded-full border border-white/5 whitespace-nowrap ml-2">
                              {activity.time_ago}
                            </span>
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <div className="h-1 flex-1 bg-white/10 rounded-full overflow-hidden">
                              <div className="h-full bg-primary/50 w-full rounded-full" />
                            </div>
                            <span className="text-xs text-primary font-medium">
                              {t("dashboard.activeDownload.completed")}
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    )
                  )
                )}
              </div>
            </div>
          </motion.div>

          <motion.div variants={item} className="col-span-1 space-y-6">
            <div className="rounded-3xl border border-white/10 bg-black/20 backdrop-blur-xl p-8 shadow-2xl">
              <h3 className="font-bold mb-6 text-2xl text-white flex items-center gap-3">
                <span className="w-1.5 h-8 bg-purple-500 rounded-full shadow-[0_0_10px_rgba(168,85,247,0.5)]"></span>
                {t("dashboard.quickActions")}
              </h3>
              <div className="space-y-4">
                <Button
                  variant="primary"
                  className="w-full justify-start h-14 text-lg font-bold shadow-lg shadow-primary/20"
                  size="lg"
                  onClick={() => navigate("/search")}
                >
                  <Download className="mr-3 h-6 w-6" />{" "}
                  {t("dashboard.actions.addDownload")}
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-start h-14 text-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-100 border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.1)] transition-all"
                  size="lg"
                  onClick={() => navigate("/search")}
                >
                  <Music className="mr-3 h-6 w-6" />{" "}
                  {t("dashboard.actions.importPlaylist")}
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start h-14 text-lg border-white/10 hover:bg-white/5 text-gray-300 hover:text-white"
                  size="lg"
                  onClick={() => navigate("/watchlist")}
                >
                  <Clock className="mr-3 h-6 w-6" />{" "}
                  {t("dashboard.actions.viewWatchlist")}
                </Button>
              </div>
            </div>

            {/* Active Download Widget */}
            {dashboardStats.active_download ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-3xl border border-primary/30 bg-linear-to-b from-black/80 to-black/60 backdrop-blur-xl p-6 shadow-[0_0_30px_rgba(var(--primary-rgb),0.1)] shadow-primary/10 relative overflow-hidden group"
              >
                {/* Background Image Blur Effect */}
                {dashboardStats.active_download.image_url && (
                  <div
                    className="absolute inset-0 opacity-20 bg-cover bg-center blur-xl pointer-events-none"
                    style={{
                      backgroundImage: `url(${dashboardStats.active_download.image_url})`,
                    }}
                  />
                )}
                <div className="w-24 h-1 bg-linear-to-r from-transparent via-primary/50 to-transparent mx-auto mt-8 rounded-full opacity-50 absolute bottom-0 left-1/2 -translate-x-1/2 blur-sm" />

                <div className="flex items-center gap-4 mb-4 relative z-10">
                  <div className="relative">
                    {dashboardStats.active_download.image_url ? (
                      <img
                        src={dashboardStats.active_download.image_url}
                        alt="Cover"
                        className="w-12 h-12 rounded-xl object-cover border border-white/10 shadow-lg"
                      />
                    ) : (
                      <div className="p-3 rounded-xl bg-primary/20 text-primary border border-primary/20 shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)] shadow-primary/30 animate-pulse">
                        <Download size={24} />
                      </div>
                    )}
                    {dashboardStats.active_download.status ===
                      "downloading" && (
                      <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-primary rounded-full border-2 border-black animate-pulse" />
                    )}
                  </div>

                  <div>
                    <span className="font-bold text-white text-lg block">
                      {dashboardStats.active_download.status === "downloading"
                        ? t("dashboard.activeDownload.downloading")
                        : t("dashboard.activeDownload.pending")}
                    </span>
                    <span className="text-xs text-primary/80 font-medium tracking-wide uppercase">
                      {Math.round(dashboardStats.active_download.progress)}%{" "}
                      {t("dashboard.activeDownload.completed")}
                    </span>
                  </div>
                </div>

                <div className="relative z-10 space-y-3">
                  <div>
                    <p className="text-white font-bold text-lg truncate leading-tight">
                      {dashboardStats.active_download.title}
                    </p>
                    <p className="text-gray-400 text-sm truncate">
                      {dashboardStats.active_download.artist}
                    </p>
                  </div>

                  <div className="h-2 bg-white/10 rounded-full overflow-hidden border border-white/5">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{
                        width: `${dashboardStats.active_download.progress}%`,
                      }}
                      transition={{ ease: "linear" }}
                      className="h-full bg-linear-to-r from-primary to-primary/80 shadow-[0_0_10px_rgba(var(--primary-rgb),0.5)] shadow-primary/50"
                    />
                  </div>
                </div>
              </motion.div>
            ) : (
              <div className="rounded-3xl border border-white/5 bg-white/5 p-6 flex flex-col items-center justify-center text-center space-y-3 min-h-[180px]">
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-gray-600">
                  <Download size={24} />
                </div>
                <p className="text-gray-500 font-medium">
                  {t("dashboard.activeDownload.noActive")}
                </p>
                <p className="text-xs text-gray-600 max-w-[150px]">
                  {t("dashboard.activeDownload.startDownloading")}
                </p>
              </div>
            )}
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
