import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, ExternalLink, Loader2, Music2, RefreshCcw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { lyricsApi } from "../../api/lyrics";
import { cn } from "../../lib/utils";
import { useStore } from "../../store/useStore";

type LyricsPanelProps = Readonly<{
  isOpen: boolean;
  onClose: () => void;
  currentTime: number;
}>;

interface LrcLine {
  time: number;
  text: string;
}

export default function LyricsPanel({ isOpen, onClose, currentTime }: LyricsPanelProps) {
  const { currentTrack } = useStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [refreshCount, setRefreshCount] = useState(0);

  // Helper to clean artist/title for better search results
  const cleanSearchTerm = (term: string, counterpart?: string) => {
    let cleaned = term
      .replaceAll(/\(Official[^)]*\)/gi, "")
      .replaceAll(/\[Official[^\]]*\]/gi, "")
      .replaceAll(/\(Video[^)]*\)/gi, "")
      .replaceAll(/\[Video[^\]]*\]/gi, "")
      .replaceAll(/\(Lyrics[^)]*\)/gi, "")
      .replaceAll(/\[Lyrics[^\]]*\]/gi, "")
      .replaceAll(/\(feat\.[^)]*\)/gi, "")
      .replaceAll(/ft\..*$/gi, "")
      .replaceAll(/\(HD\)/gi, "")
      .replaceAll(/\(HQ\)/gi, "");

    if (counterpart) {
      const escapedCounterpart = counterpart.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      // nosemgrep: detect-non-literal-regexp — escapedCounterpart is sanitized via regex escaping above
      cleaned = cleaned
        .replace(new RegExp(`^${escapedCounterpart}\\s*-\\s*`, "i"), "")
        .replace(new RegExp(`\\s*-\\s*${escapedCounterpart}$`, "i"), "");
    }

    return cleaned.trim();
  };

  const {
    data: lyrics,
    isLoading,
    isRefetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ["lyrics", currentTrack?.artist, currentTrack?.title, refreshCount],
    queryFn: async () => {
      if (!currentTrack?.artist || !currentTrack?.title) {
        return null;
      }
      const artist = cleanSearchTerm(currentTrack.artist);
      const title = cleanSearchTerm(currentTrack.title, artist);

      console.log(`Searching lyrics for: "${artist}" - "${title}" (Refresh: ${refreshCount > 0})`);
      return lyricsApi.search(artist, title, refreshCount === 0);
    },
    enabled: isOpen && !!currentTrack?.artist && !!currentTrack?.title,
    staleTime: 1000 * 60 * 60, // 1 hour
    retry: 1,
  });

  const handleRefresh = () => {
    setRefreshCount((prev) => prev + 1);
  };

  // Reset refresh count when track changes
  useEffect(() => {
    if (refreshCount !== 0) {
      setRefreshCount(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrack?.id]);

  // Robust LRC Parser
  const parseLrc = (lrc: string): LrcLine[] => {
    if (!lrc) return [];

    const lines = lrc.split("\n");
    const result: LrcLine[] = [];
    const timeReg = /\[(\d+):(\d+)([:.](\d+))?\]/g;

    lines.forEach((line) => {
      const times = line.match(timeReg);
      if (!times) return;

      const text = line.replace(timeReg, "").trim();

      times.forEach((t) => {
        const match = /\[(\d+):(\d+)([:.](\d+))?\]/.exec(t);
        if (match) {
          const min = Number.parseInt(match[1]);
          const sec = Number.parseInt(match[2]);
          const fraction = match[4] ? Number.parseInt(match[4]) : 0;

          let time = min * 60 + sec;
          if (match[3]?.startsWith(".") || match[3]?.startsWith(":")) {
            const digits = match[4]?.length || 0;
            time += fraction / Math.pow(10, digits);
          }

          result.push({ time, text });
        }
      });
    });

    return result.sort((a, b) => a.time - b.time);
  };

  const syncedLyrics = lyrics?.synced_lyrics ? parseLrc(lyrics.synced_lyrics) : null;

  // Find active line index
  const activeLineIndex =
    syncedLyrics && syncedLyrics.length > 0
      ? [...syncedLyrics].reverse().findIndex((line) => line.time <= currentTime)
      : -1;

  const actualIndex =
    syncedLyrics && activeLineIndex !== -1 ? syncedLyrics.length - 1 - activeLineIndex : -1;

  // Debug logging for time synchronization
  useEffect(() => {
    if (isOpen && syncedLyrics && syncedLyrics.length > 0) {
      // Only log every few seconds to avoid console flood
      if (Math.floor(currentTime) % 5 === 0) {
        console.debug(`Lyrics sync: time=${currentTime.toFixed(2)}s, index=${actualIndex}`);
      }
    }
  }, [currentTime, isOpen, syncedLyrics, actualIndex]);

  // Auto-scroll to active line
  useEffect(() => {
    if (actualIndex >= 0 && scrollRef.current) {
      const activeElement = scrollRef.current.children[actualIndex] as HTMLElement;
      if (activeElement) {
        activeElement.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    }
  }, [actualIndex]);

  // Refetch when track changes
  useEffect(() => {
    if (isOpen && currentTrack) {
      refetch();
    }
  }, [currentTrack, isOpen, refetch]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          />

          {/* Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-card/95 backdrop-blur-xl border-l border-border z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="flex items-center gap-3">
                <Music2 className="w-5 h-5 text-primary" />
                <h2 className="text-lg font-semibold">Lyrics</h2>
                {lyrics?.found && (
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider",
                      syncedLyrics && syncedLyrics.length > 0
                        ? "bg-primary/20 text-primary border border-primary/30"
                        : "bg-muted text-muted-foreground border border-border"
                    )}
                  >
                    {syncedLyrics && syncedLyrics.length > 0 ? "Karaoke" : "Plain"}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRefresh}
                  disabled={isLoading || isRefetching}
                  className={cn(
                    "p-2 hover:bg-muted rounded-lg transition-colors",
                    (isLoading || isRefetching) && "opacity-50 cursor-not-allowed"
                  )}
                  title="Refresh lyrics"
                >
                  <RefreshCcw
                    className={cn("w-5 h-5", (isLoading || isRefetching) && "animate-spin")}
                  />
                </button>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-muted rounded-lg transition-colors"
                  id="close-lyrics-panel"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Track Info */}
            {currentTrack && (
              <div className="p-4 border-b border-border bg-muted/30">
                <p className="font-medium text-foreground truncate">{currentTrack.title}</p>
                <p className="text-sm text-muted-foreground truncate">{currentTrack.artist}</p>
              </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              {(() => {
                if (!currentTrack) {
                  return (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                      <Music2 className="w-12 h-12 mb-4 opacity-50" />
                      <p>No track playing</p>
                    </div>
                  );
                }

                if (isLoading) {
                  return (
                    <div className="flex flex-col items-center justify-center h-full">
                      <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
                      <p className="text-muted-foreground">Fetching lyrics...</p>
                    </div>
                  );
                }

                if (error) {
                  return (
                    <div className="flex flex-col items-center justify-center h-full text-destructive">
                      <AlertCircle className="w-12 h-12 mb-4" />
                      <p>Failed to load lyrics</p>
                      <button
                        onClick={() => {
                          console.log("Retrying lyrics fetch...");
                          refetch();
                        }}
                        className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                      >
                        Try Again
                      </button>
                    </div>
                  );
                }

                const hasNoLyrics = !lyrics?.found || (!lyrics?.lyrics && !lyrics?.synced_lyrics);
                if (hasNoLyrics) {
                  return (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                      <Music2 className="w-12 h-12 mb-4 opacity-50" />
                      <p>No lyrics found for this song</p>
                    </div>
                  );
                }

                return (
                  <div className="space-y-8 pb-32">
                    {syncedLyrics && syncedLyrics.length > 0 ? (
                      /* Synced Lyrics View */
                      <div ref={scrollRef} className="space-y-6">
                        {syncedLyrics.map((line, index) => (
                          <motion.p
                            key={`${index}-${line.time}`}
                            animate={{
                              opacity: actualIndex === index ? 1 : 0.4,
                              scale: actualIndex === index ? 1.05 : 1,
                              color: actualIndex === index ? "var(--primary)" : "var(--foreground)",
                            }}
                            className={cn(
                              "text-xl md:text-2xl font-bold leading-tight transition-colors duration-300 cursor-pointer hover:text-primary/70",
                              actualIndex === index ? "text-primary" : "text-foreground"
                            )}
                          >
                            {line.text || "♪"}
                          </motion.p>
                        ))}
                      </div>
                    ) : (
                      /* Plain Lyrics Fallback */
                      <pre className="whitespace-pre-wrap font-sans text-foreground leading-relaxed text-lg">
                        {lyrics?.lyrics}
                      </pre>
                    )}

                    {/* Source Link */}
                    {lyrics?.url && (
                      <a
                        href={lyrics.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-sm text-primary hover:underline mt-8"
                      >
                        View on Genius
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                );
              })()}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
