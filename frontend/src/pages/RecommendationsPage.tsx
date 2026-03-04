import React, { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import { useTranslation } from "react-i18next";
import { IoMusicalNote, IoRefresh } from "react-icons/io5";
import { SiLastdotfm } from "react-icons/si";
import { useNavigate, useSearchParams } from "react-router-dom";
import ArtistRecommendationCard from "../components/dashboard/ArtistRecommendationCard";
import LastfmProfileCard from "../components/dashboard/LastfmProfileCard";
import PlaylistRecommendationCard from "../components/dashboard/PlaylistRecommendationCard";
import RecommendationCard from "../components/dashboard/RecommendationCard";
import api from "../services/api";
import {
  callbackLastfm,
  connectLastfm,
  disconnectLastfm,
  getLastfmStatus,
  getRecommendations,
} from "../services/lastfm";
import { useStore } from "../store/useStore";
import type { LastfmStatus, RecommendationResponse, RecommendedTrack } from "../types/lastfm";

const RecommendationsPage: React.FC = () => {
  const { t } = useTranslation();
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [status, setStatus] = useState<LastfmStatus>({ connected: false, username: null });
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"tracks" | "artists" | "playlists">("tracks");
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Store actions
  const { playTrack } = useStore();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      handleCallback(token);
    } else {
      checkStatus();
    }
  }, [searchParams]);

  const handleCallback = async (token: string) => {
    try {
      setLoading(true);
      await callbackLastfm(token);
      toast.success(t("lastfm.connected", "Successfully connected to Last.fm!"));
      navigate("/recommendations", { replace: true });
      checkStatus();
    } catch (e) {
      console.error("Callback failed", e);
      toast.error(t("lastfm.error", "Failed to connect to Last.fm"));
      navigate("/recommendations", { replace: true });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (status.connected) {
      fetchRecommendations();
    }
  }, [status.connected]);

  const checkStatus = async () => {
    try {
      const s = await getLastfmStatus();
      setStatus(s);
    } catch (e) {
      console.error("Failed to check Last.fm status", e);
    }
  };

  const fetchRecommendations = async (force = false) => {
    try {
      if (force) setRefreshing(true);
      else setLoading(true);

      const data = await getRecommendations(force);
      setRecommendations(data);
    } catch (e) {
      console.error("Failed to fetch recommendations", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleConnect = async () => {
    try {
      const { auth_url } = await connectLastfm();
      window.open(auth_url, "_blank");
    } catch (e) {
      console.error("Failed to start connection", e);
    }
  };

  const handleDisconnect = async () => {
    try {
      await disconnectLastfm();
      await checkStatus();
      setRecommendations(null);
    } catch (e) {
      console.error("Disconnect failed", e);
    }
  };

  const handlePlayTrack = async (track: RecommendedTrack) => {
    const toastId = toast.loading(`Finding ${track.name}...`);
    try {
      // Search via unified browse endpoint (aggregates Deezer, MusicBrainz, Spotify)
      const query = `${track.artist} ${track.name}`;
      const { data } = await api.get("/browse/search", {
        params: { q: query, type: "track", limit: 1 },
      });

      if (data && data.length > 0) {
        const foundTrack = data[0];
        // Source comes from browse endpoint (deezer, spotify, musicbrainz)
        if (!foundTrack.source) foundTrack.source = "deezer";

        playTrack(foundTrack);
        toast.dismiss(toastId);
        toast.success(`Playing ${foundTrack.name}`);
      } else {
        toast.error("Track not found in libraries", { id: toastId });
      }
    } catch (e) {
      console.error("Play error", e);
      toast.error("Failed to play track", { id: toastId });
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <IoMusicalNote className="text-primary" />
            {t("recommendations.title", "Music Discovery")}
          </h1>
          <p className="text-zinc-400 mt-1">
            {t("recommendations.subtitle", "Personalized picks based on your listening habits")}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {!status.connected ? (
            <button
              onClick={handleConnect}
              className="cursor-pointer px-4 py-2 bg-[#ba0000] hover:bg-[#d51007] text-white rounded-lg font-medium flex items-center gap-2 transition-colors shadow-lg shadow-red-900/20"
            >
              <SiLastdotfm size={20} />
              {t("lastfm.connect", "Connect Last.fm")}
            </button>
          ) : (
            <div className="flex items-center gap-4 bg-zinc-900/50 border border-white/5 px-4 py-2 rounded-lg">
              <div className="flex items-center gap-2">
                <SiLastdotfm className="text-[#ba0000]" size={20} />
                <span className="text-sm">
                  Connected as <span className="font-bold text-white">{status.username}</span>
                </span>
              </div>
              <button
                onClick={handleDisconnect}
                className="text-xs text-zinc-500 hover:text-white underline"
              >
                {t("common.disconnect", "Disconnect")}
              </button>
            </div>
          )}
        </div>
      </div>

      {status.connected && status.username && (
        <div className="mb-8">
          <LastfmProfileCard username={status.username} />
        </div>
      )}

      {!status.connected ? (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-zinc-900/30 border border-white/5 rounded-2xl border-dashed">
          <div className="w-16 h-16 bg-[#ba0000]/10 text-[#ba0000] rounded-full flex items-center justify-center mb-4">
            <SiLastdotfm size={32} />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Connect Last.fm to get started</h2>
          <p className="text-zinc-400 max-w-md mb-6">
            To generate personalized recommendations, we need to analyze your listening history.
            Connect your Last.fm account to sync your scrobbles.
          </p>
          <button
            onClick={handleConnect}
            className="px-6 py-3 bg-white text-black font-bold rounded-full hover:scale-105 transition-transform"
          >
            Connect Account
          </button>
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-1 p-1 bg-zinc-900/80 backdrop-blur rounded-xl border border-white/5 w-fit mb-8 shadow-inner">
            <button
              onClick={() => setActiveTab("tracks")}
              className={`cursor-pointer px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${
                activeTab === "tracks"
                  ? "bg-primary text-white shadow-lg shadow-primary/25 scale-[1.02]"
                  : "text-zinc-500 hover:text-white hover:bg-white/5"
              }`}
            >
              Tracks
            </button>
            <button
              onClick={() => setActiveTab("artists")}
              className={`cursor-pointer px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${
                activeTab === "artists"
                  ? "bg-primary text-white shadow-lg shadow-primary/25 scale-[1.02]"
                  : "text-zinc-500 hover:text-white hover:bg-white/5"
              }`}
            >
              Artists
            </button>
            <button
              onClick={() => setActiveTab("playlists")}
              className={`cursor-pointer px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${
                activeTab === "playlists"
                  ? "bg-primary text-white shadow-lg shadow-primary/25 scale-[1.02]"
                  : "text-zinc-500 hover:text-white hover:bg-white/5"
              }`}
            >
              Playlists
            </button>
          </div>

          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-zinc-400">Source:</span>
              <span className="px-2 py-1 bg-zinc-800 rounded text-xs text-white border border-white/10 uppercase font-bold tracking-wider">
                {recommendations?.source || "Loading..."}
              </span>
              {recommendations?.cache_status === "hit" && (
                <span className="text-xs text-zinc-600">Cached</span>
              )}
            </div>

            <button
              onClick={() => fetchRecommendations(true)}
              disabled={refreshing || loading}
              className="cursor-pointer p-2 text-zinc-400 hover:text-white bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh Recommendations"
            >
              <IoRefresh className={refreshing ? "animate-spin" : ""} size={20} />
            </button>
          </div>

          {loading && !refreshing ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
              {[...new Array(10)].map((_, i) => (
                <div key={i} className="aspect-[3/4] bg-zinc-900 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <>
              {activeTab === "tracks" &&
                (recommendations?.tracks && recommendations.tracks.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                    {recommendations.tracks.map((track, idx) => (
                      <RecommendationCard
                        key={`${track.artist}-${track.name}-${idx}`}
                        track={track}
                        onPlay={handlePlayTrack}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-20 text-zinc-500 bg-zinc-900/20 rounded-2xl border border-white/5">
                    <p>No track recommendations found. Try listening to more music!</p>
                  </div>
                ))}

              {activeTab === "artists" &&
                (recommendations?.artists && recommendations.artists.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                    {recommendations.artists.map((artist, idx) => (
                      <ArtistRecommendationCard key={`${artist.name}-${idx}`} artist={artist} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-20 text-zinc-500 bg-zinc-900/20 rounded-2xl border border-white/5">
                    <p>No artist recommendations found yet.</p>
                  </div>
                ))}

              {activeTab === "playlists" &&
                (recommendations?.playlists && recommendations.playlists.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                    {recommendations.playlists.map((playlist, idx) => (
                      <PlaylistRecommendationCard
                        key={`${playlist.id}-${idx}`}
                        playlist={playlist}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-20 text-zinc-500 bg-zinc-900/20 rounded-2xl border border-white/5">
                    <p>No playlist recommendations found yet.</p>
                  </div>
                ))}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default RecommendationsPage;
