import React, { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import { useTranslation } from "../hooks/useTranslation";
import { IoMusicalNote, IoRefresh } from "react-icons/io5";
import { SiLastdotfm, SiMusicbrainz } from "react-icons/si";
import { useNavigate, useSearchParams } from "react-router-dom";
import ArtistRecommendationCard from "../components/dashboard/ArtistRecommendationCard";
import LastfmProfileCard from "../components/dashboard/LastfmProfileCard";
import PlaylistRecommendationCard from "../components/dashboard/PlaylistRecommendationCard";
import RecommendationCard from "../components/dashboard/RecommendationCard";
import api from "../services/api";
import { callbackLastfm, getRecommendations } from "../services/lastfm";
import {
  connectRedirectProvider,
  connectTokenProvider,
  disconnectProvider,
  getProviders,
  setListeningPreference,
} from "../services/listening";
import { useStore } from "../store/useStore";
import type { RecommendationResponse, RecommendedTrack } from "../types/lastfm";
import type { ProviderInfo } from "../types/listening";

const GRID_CLASS = "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6";
const SKELETON_KEYS = Array.from({ length: 10 }, (_, i) => `rec-skeleton-${i}`);

const PROVIDER_ICON: Record<string, React.ReactNode> = {
  lastfm: <SiLastdotfm size={20} />,
  listenbrainz: <SiMusicbrainz size={20} />,
};

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="text-center py-20 text-zinc-500 bg-card/20 rounded-2xl border border-white/5">
    <p>{message}</p>
  </div>
);

const RecommendationsPage: React.FC = () => {
  const { t } = useTranslation();
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [preference, setPreference] = useState<string>("auto");
  const [lbToken, setLbToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"tracks" | "artists" | "playlists">("tracks");
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const { playTrack } = useStore();

  const connected = providers.filter((p) => p.connected);
  const anyConnected = connected.length > 0;
  const lastfm = providers.find((p) => p.name === "lastfm");

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      // eslint-disable-next-line react-hooks/immutability
      handleLastfmCallback(token);
    } else {
      // eslint-disable-next-line react-hooks/immutability
      loadProviders();
    }
  }, [searchParams]);

  useEffect(() => {
    if (anyConnected) {
      // eslint-disable-next-line react-hooks/immutability
      fetchRecommendations();
    }
  }, [anyConnected]);

  const loadProviders = async () => {
    try {
      const data = await getProviders();
      setProviders(data.providers);
      setPreference(data.preference);
    } catch (e) {
      console.error("Failed to load listening providers", e);
    }
  };

  const fetchRecommendations = async (force = false) => {
    try {
      if (force) setRefreshing(true);
      else setLoading(true);
      const data = await getRecommendations(force);
      setRecommendations(data);
      if (force) toast.success(t("recommendations.refreshed", "Fresh picks loaded"));
    } catch (e) {
      console.error("Failed to fetch recommendations", e);
      if (force) toast.error(t("recommendations.refreshError", "Failed to refresh recommendations"));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleLastfmCallback = async (token: string) => {
    try {
      setLoading(true);
      await callbackLastfm(token);
      toast.success(t("lastfm.connected", "Successfully connected to Last.fm!"));
      navigate("/recommendations", { replace: true });
      loadProviders();
    } catch (e) {
      console.error("Callback failed", e);
      toast.error(t("lastfm.error", "Failed to connect to Last.fm"));
      navigate("/recommendations", { replace: true });
    } finally {
      setLoading(false);
    }
  };

  const handleConnectRedirect = async (provider: string) => {
    try {
      const { auth_url } = await connectRedirectProvider(provider);
      window.open(auth_url, "_blank");
    } catch (e) {
      console.error("Failed to start connection", e);
    }
  };

  const handleConnectToken = async (provider: string) => {
    if (!lbToken.trim()) return;
    try {
      const { username } = await connectTokenProvider(provider, lbToken.trim());
      setLbToken("");
      toast.success(t("listening.connectedAs", "Connected as {name}").replace("{name}", username));
      await loadProviders();
    } catch (e: unknown) {
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        t("listening.tokenError", "Invalid token");
      toast.error(detail);
    }
  };

  const handleDisconnect = async (provider: string) => {
    try {
      await disconnectProvider(provider);
      await loadProviders();
      setRecommendations(null);
    } catch (e) {
      console.error("Disconnect failed", e);
    }
  };

  const handlePickSource = async (provider: string) => {
    setPreference(provider);
    try {
      await setListeningPreference(provider);
      await fetchRecommendations(true);
    } catch (e) {
      console.error("Failed to set recommendation source", e);
    }
  };

  const handlePlayTrack = async (track: RecommendedTrack) => {
    const toastId = toast.loading(`Finding ${track.name}...`);
    try {
      const query = `${track.artist} ${track.name}`;
      const { data } = await api.get("/browse/search", {
        params: { q: query, type: "track", limit: 1 },
      });
      if (data && data.length > 0) {
        const foundTrack = data[0];
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

  const renderTabContent = () => {
    if (activeTab === "tracks") {
      const tracks = recommendations?.tracks ?? [];
      return tracks.length > 0 ? (
        <div className={GRID_CLASS}>
          {tracks.map((track, idx) => (
            <RecommendationCard
              key={`${track.artist}-${track.name}-${idx}`}
              track={track}
              onPlay={handlePlayTrack}
            />
          ))}
        </div>
      ) : (
        <EmptyState message="No track recommendations found. Try listening to more music!" />
      );
    }

    if (activeTab === "artists") {
      const artists = recommendations?.artists ?? [];
      return artists.length > 0 ? (
        <div className={GRID_CLASS}>
          {artists.map((artist, idx) => (
            <ArtistRecommendationCard key={`${artist.name}-${idx}`} artist={artist} />
          ))}
        </div>
      ) : (
        <EmptyState message="No artist recommendations found yet." />
      );
    }

    const playlists = recommendations?.playlists ?? [];
    return playlists.length > 0 ? (
      <div className={GRID_CLASS}>
        {playlists.map((playlist, idx) => (
          <PlaylistRecommendationCard key={`${playlist.id}-${idx}`} playlist={playlist} />
        ))}
      </div>
    ) : (
      <EmptyState message="No playlist recommendations found yet." />
    );
  };

  const renderConnectAction = (p: ProviderInfo) => {
    if (p.connected) {
      return (
        <>
          <span className="text-sm">
            {p.display_name} &middot; <span className="font-bold text-white">{p.username}</span>
          </span>
          <button
            onClick={() => handleDisconnect(p.name)}
            className="text-xs text-zinc-500 hover:text-white underline"
          >
            {t("common.disconnect", "Disconnect")}
          </button>
        </>
      );
    }
    if (p.connects_with_token) {
      return (
        <div className="flex items-center gap-2">
          <input
            type="password"
            value={lbToken}
            onChange={(e) => setLbToken(e.target.value)}
            placeholder={t("listening.tokenPlaceholder", "Paste your token")}
            className="px-3 py-1.5 rounded-md bg-background border border-white/10 text-sm text-white w-56 focus:outline-none focus:border-primary/50"
          />
          <button
            onClick={() => handleConnectToken(p.name)}
            className="px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-sm font-medium"
          >
            {t("listening.connect", "Connect")} {p.display_name}
          </button>
        </div>
      );
    }
    return (
      <button
        onClick={() => handleConnectRedirect(p.name)}
        className="px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-sm font-medium"
      >
        {t("listening.connect", "Connect")} {p.display_name}
      </button>
    );
  };

  const renderConnectRow = (p: ProviderInfo) => (
    <div
      key={p.name}
      className="flex items-center gap-3 bg-card/50 border border-white/5 px-4 py-2 rounded-lg"
    >
      <span className="text-primary">{PROVIDER_ICON[p.name]}</span>
      {renderConnectAction(p)}
    </div>
  );

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <IoMusicalNote className="text-primary" />
            {t("recommendations.title", "Music Discovery")}
          </h1>
          <p className="text-zinc-400 mt-1">
            {t("recommendations.subtitle", "Personalized picks based on your listening habits")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">{providers.map(renderConnectRow)}</div>

        {connected.length > 1 && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-zinc-400">
              {t("listening.recommendationSource", "Recommendation source")}:
            </span>
            {connected
              .filter((p) => p.supports_recommendations)
              .map((p) => (
                <button
                  key={p.name}
                  onClick={() => handlePickSource(p.name)}
                  className={`px-3 py-1 rounded-full text-xs font-bold transition-colors ${
                    preference === p.name
                      ? "bg-primary text-primary-foreground"
                      : "bg-card/60 text-zinc-400 hover:text-white"
                  }`}
                >
                  {p.display_name}
                </button>
              ))}
            <button
              onClick={() => handlePickSource("auto")}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-colors ${
                preference === "auto"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card/60 text-zinc-400 hover:text-white"
              }`}
            >
              {t("listening.auto", "Auto")}
            </button>
          </div>
        )}
      </div>

      {lastfm?.connected && lastfm.username && (
        <div className="mb-8">
          <LastfmProfileCard username={lastfm.username} />
        </div>
      )}

      {!anyConnected ? (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-card/30 border border-white/5 rounded-2xl border-dashed">
          <div className="w-16 h-16 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
            <IoMusicalNote size={32} />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">
            {t("listening.connectPrompt", "Connect a listening service to get started")}
          </h2>
          <p className="text-zinc-400 max-w-md mb-2">
            {t(
              "listening.connectHint",
              "Connect Last.fm or ListenBrainz so we can analyze your listening history."
            )}
          </p>
          <a
            href="https://listenbrainz.org/settings/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary text-sm hover:underline"
          >
            {t("listening.getToken", "Where do I get a ListenBrainz token?")}
          </a>
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-1 p-1 bg-card/80 backdrop-blur rounded-xl border border-white/5 w-fit mb-8 shadow-inner">
            {(["tracks", "artists", "playlists"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`cursor-pointer px-5 py-2.5 rounded-lg text-sm font-bold transition-all capitalize ${
                  activeTab === tab
                    ? "bg-primary text-white shadow-lg shadow-primary/25 scale-[1.02]"
                    : "text-zinc-500 hover:text-white hover:bg-white/5"
                }`}
              >
                {t(`recommendations.tabs.${tab}`, tab)}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-end mb-6">
            <button
              onClick={() => fetchRecommendations(true)}
              disabled={refreshing || loading}
              className="cursor-pointer p-2 text-zinc-400 hover:text-white bg-secondary hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
              title="Refresh Recommendations"
            >
              <IoRefresh className={refreshing ? "animate-spin" : ""} size={20} />
            </button>
          </div>

          {loading && !refreshing ? (
            <div className={GRID_CLASS}>
              {SKELETON_KEYS.map((key) => (
                <div key={key} className="aspect-3/4 bg-card rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            renderTabContent()
          )}
        </div>
      )}
    </div>
  );
};

export default RecommendationsPage;
