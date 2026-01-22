import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, ExternalLink, Loader2, Music2, X } from "lucide-react";
import { useEffect } from "react";
import { lyricsApi } from "../../api/lyrics";
import { useStore } from "../../store/useStore";

interface LyricsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LyricsPanel({ isOpen, onClose }: LyricsPanelProps) {
  const { currentTrack } = useStore();

  const {
    data: lyrics,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["lyrics", currentTrack?.artist, currentTrack?.title],
    queryFn: () => {
      if (!currentTrack?.artist || !currentTrack?.title) {
        return null;
      }
      return lyricsApi.search(currentTrack.artist, currentTrack.title);
    },
    enabled: isOpen && !!currentTrack?.artist && !!currentTrack?.title,
    staleTime: 1000 * 60 * 60, // 1 hour
    retry: 1,
  });

  // Refetch when track changes
  useEffect(() => {
    if (isOpen && currentTrack) {
      refetch();
    }
  }, [currentTrack?.id, isOpen, refetch]);

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
              </div>
              <button onClick={onClose} className="p-2 hover:bg-muted rounded-lg transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Track Info */}
            {currentTrack && (
              <div className="p-4 border-b border-border bg-muted/30">
                <p className="font-medium text-foreground truncate">{currentTrack.title}</p>
                <p className="text-sm text-muted-foreground truncate">{currentTrack.artist}</p>
              </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {!currentTrack ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <Music2 className="w-12 h-12 mb-4 opacity-50" />
                  <p>No track playing</p>
                </div>
              ) : isLoading ? (
                <div className="flex flex-col items-center justify-center h-full">
                  <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
                  <p className="text-muted-foreground">Fetching lyrics...</p>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center h-full text-destructive">
                  <AlertCircle className="w-12 h-12 mb-4" />
                  <p>Failed to load lyrics</p>
                  <button
                    onClick={() => refetch()}
                    className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              ) : !lyrics?.found ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <Music2 className="w-12 h-12 mb-4 opacity-50" />
                  <p>No lyrics found for this song</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Lyrics Text */}
                  <pre className="whitespace-pre-wrap font-sans text-foreground leading-relaxed">
                    {lyrics.lyrics}
                  </pre>

                  {/* Source Link */}
                  {lyrics.url && (
                    <a
                      href={lyrics.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-primary hover:underline mt-4"
                    >
                      View on Genius
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
