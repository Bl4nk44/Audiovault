import React, { useEffect, useState } from "react";
import { useTranslation } from "../../hooks/useTranslation";
import {
  IoCalendarOutline,
  IoDisc,
  IoGlobeOutline,
  IoMusicalNotes,
  IoPeople,
  IoPersonCircle,
} from "react-icons/io5";
import { SiLastdotfm } from "react-icons/si";
import { getLastfmProfile } from "../../services/lastfm";
import type { LastfmProfile } from "../../types/lastfm";

interface LastfmProfileCardProps {
  username: string;
}

export const LastfmProfileCard: React.FC<LastfmProfileCardProps> = ({ username }) => {
  const { t, language } = useTranslation();
  const [profile, setProfile] = useState<LastfmProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        const data = await getLastfmProfile();
        setProfile(data);
      } catch (err) {
        console.error("Failed to fetch Last.fm profile:", err);
        setError(t("lastfm.profile.error", "Failed to load profile"));
      } finally {
        setLoading(false);
      }
    };

    if (username) {
      fetchProfile();
    }
  }, [username, t]);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  const formatDate = (unixTime: number): string => {
    if (!unixTime) return "";
    return new Date(unixTime * 1000).toLocaleDateString(language, {
      year: "numeric",
      month: "short",
    });
  };

  if (loading) {
    return (
      <div className="bg-card/50 rounded-xl p-4 border border-white/5 animate-pulse">
        <div className="h-20 bg-secondary rounded-lg" />
      </div>
    );
  }

  if (error || !profile) {
    return null;
  }

  const { user, friends } = profile;

  return (
    <div className="bg-gradient-to-br from-card to-background rounded-xl p-5 border border-white/5 shadow-xl">
      {/* User Stats */}
      <div className="flex items-start gap-4 mb-5">
        {/* Avatar */}
        <div className="relative">
          {user.image_url ? (
            <img
              src={user.image_url}
              alt={user.name}
              className="w-16 h-16 rounded-full object-cover border-2 border-red-500"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center border-2 border-red-500">
              <IoPersonCircle className="w-10 h-10 text-zinc-500" />
            </div>
          )}
          <div className="absolute -bottom-1 -right-1 bg-red-500 rounded-full p-1">
            <SiLastdotfm className="w-3 h-3 text-white" />
          </div>
        </div>

        {/* User Info */}
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-white text-lg truncate">{user.realname || user.name}</h3>
          <a
            href={user.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-red-400 text-sm hover:underline"
          >
            @{user.name}
          </a>
          <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
            {user.country && (
              <span className="flex items-center gap-1">
                <IoGlobeOutline /> {user.country}
              </span>
            )}
            {user.registered > 0 && (
              <span className="flex items-center gap-1">
                <IoCalendarOutline /> {formatDate(user.registered)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        <div className="bg-secondary/50 rounded-lg p-3 text-center">
          <div className="text-red-400 font-bold text-lg">{formatNumber(user.playcount)}</div>
          <div className="text-xs text-zinc-500 flex items-center justify-center gap-1">
            <IoMusicalNotes className="w-3 h-3" />
            Scrobbles
          </div>
        </div>
        <div className="bg-secondary/50 rounded-lg p-3 text-center">
          <div className="text-primary font-bold text-lg">{formatNumber(user.artist_count)}</div>
          <div className="text-xs text-zinc-500 flex items-center justify-center gap-1">
            <IoPeople className="w-3 h-3" />
            {t("lastfm.profile.artists", "Artists")}
          </div>
        </div>
        <div className="bg-secondary/50 rounded-lg p-3 text-center">
          <div className="text-emerald-400 font-bold text-lg">{formatNumber(user.track_count)}</div>
          <div className="text-xs text-zinc-500 flex items-center justify-center gap-1">
            <IoMusicalNotes className="w-3 h-3" />
            {t("lastfm.profile.tracks", "Tracks")}
          </div>
        </div>
        <div className="bg-secondary/50 rounded-lg p-3 text-center">
          <div className="text-amber-400 font-bold text-lg">{formatNumber(user.album_count)}</div>
          <div className="text-xs text-zinc-500 flex items-center justify-center gap-1">
            <IoDisc className="w-3 h-3" />
            {t("lastfm.profile.albums", "Albums")}
          </div>
        </div>
      </div>

      {/* Friends */}
      {friends.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-zinc-400 mb-3 flex items-center gap-2">
            <IoPeople /> {t("lastfm.profile.friends", "Friends")} ({friends.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {friends.map((friend) => (
              <a
                key={friend.name}
                href={friend.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center gap-2 bg-secondary/50 hover:bg-muted/50 rounded-full px-3 py-1.5 transition-colors"
                title={friend.realname || friend.name}
              >
                {friend.image_url ? (
                  <img
                    src={friend.image_url}
                    alt={friend.name}
                    className="w-6 h-6 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                    <IoPersonCircle className="w-4 h-4 text-zinc-500" />
                  </div>
                )}
                <span className="text-sm text-zinc-300 group-hover:text-white truncate max-w-[80px]">
                  {friend.name}
                </span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LastfmProfileCard;
