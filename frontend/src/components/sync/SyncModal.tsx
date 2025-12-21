import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, AlertTriangle, CheckCircle, Trash2, X } from "lucide-react";
import { syncApi, type SyncReport, type SyncResult } from "../../api/sync";
import { notify as toast } from "../../utils/notify";
import { cn } from "../../lib/utils";
import { type WatchlistItem } from "../../types";

interface SyncModalProps {
  item: WatchlistItem | null; // Watchlist Item
  onClose: () => void;
}

export default function SyncModal({ item, onClose }: SyncModalProps) {
  const [step, setStep] = useState<
    "analyzing" | "review" | "executing" | "success"
  >("analyzing");
  const [report, setReport] = useState<SyncReport | null>(null);
  const [selectedRemovals, setSelectedRemovals] = useState<string[]>([]);
  const [result, setResult] = useState<SyncResult | null>(null);

  useEffect(() => {
    if (item) {
      const analyzeItem = async () => {
        setStep("analyzing");
        setReport(null);
        try {
          const data = await syncApi.analyze(item.id);
          setReport(data);
          setSelectedRemovals(data.to_remove_items.map((i) => i.track_id));
          setStep("review");
        } catch (err) {
          console.error(err);
          toast.error("Analysis failed. See console.");
          onClose();
        }
      };

      analyzeItem();
    }
  }, [item, onClose]);

  const handleExecute = async () => {
    if (!report || !item) return;
    setStep("executing");
    try {
      const res = await syncApi.execute(
        item.id,
        report.sync_token,
        selectedRemovals
      );
      setResult(res);
      setStep("success");
      toast.success("Sync completed successfully");
    } catch (err) {
      console.error(err);
      toast.error("Execution failed");
      setStep("review");
    }
  };

  if (!item) return null;

  return createPortal(
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm"
        />

        {/* Modal Content */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-2xl bg-card border border-border rounded-xl shadow-2xl overflow-hidden max-h-[85vh] flex flex-col pointer-events-auto"
        >
          {/* Header */}
          <div className="p-6 border-b border-border flex justify-between items-start bg-secondary/20">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <span className="text-primary">Sync</span> {item.source_name}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Synchronize local files with remote playlist state.
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 min-h-[300px]">
            {step === "analyzing" && (
              <div className="flex flex-col items-center justify-center h-64 gap-4">
                <Loader2 className="w-10 h-10 animate-spin text-primary" />
                <p className="text-muted-foreground">
                  Analyzing playlist state...
                </p>
              </div>
            )}

            {step === "review" && report && (
              <div className="space-y-6">
                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="p-4 bg-secondary/30 rounded-lg border border-border/50">
                    <div className="text-2xl font-bold">
                      {report.local_count}
                    </div>
                    <div className="text-xs text-muted-foreground uppercase tracking-wider">
                      Local Tracks
                    </div>
                  </div>
                  <div className="p-4 bg-secondary/30 rounded-lg border border-border/50">
                    <div className="text-2xl font-bold">
                      {report.remote_count}
                    </div>
                    <div className="text-xs text-muted-foreground uppercase tracking-wider">
                      Remote Tracks
                    </div>
                  </div>
                </div>

                {/* Warning */}
                {report.safety_warning && (
                  <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 flex gap-3 text-destructive">
                    <AlertTriangle className="h-5 w-5 shrink-0" />
                    <div>
                      <h4 className="font-bold text-sm">Safety Warning</h4>
                      <p className="text-sm opacity-90">
                        {report.warning_message}
                      </p>
                    </div>
                  </div>
                )}

                {/* Content */}
                {report.to_remove_count === 0 ? (
                  <div className="text-center py-8 text-green-400 bg-green-400/5 rounded-xl border border-green-400/10">
                    <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-80" />
                    <p className="font-medium">Library is in sync.</p>
                    <p className="text-sm opacity-70">
                      No tracks need to be removed.
                    </p>
                  </div>
                ) : (
                  <div>
                    <h3 className="text-sm font-medium mb-3 flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Trash2 size={16} className="text-destructive" />
                        Tracks to Remove ({selectedRemovals.length})
                      </span>
                      <span className="text-xs text-muted-foreground">
                        Uncheck to keep
                      </span>
                    </h3>
                    <div className="border border-border/50 rounded-lg divide-y divide-border/50 max-h-60 overflow-y-auto bg-black/20">
                      {report.to_remove_items.map((track) => (
                        <label
                          key={track.track_id}
                          className="flex items-center gap-3 p-3 hover:bg-white/5 cursor-pointer transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={selectedRemovals.includes(track.track_id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedRemovals([
                                  ...selectedRemovals,
                                  track.track_id,
                                ]);
                              } else {
                                setSelectedRemovals(
                                  selectedRemovals.filter(
                                    (id) => id !== track.track_id
                                  )
                                );
                              }
                            }}
                            className="rounded border-white/20 bg-black/20 w-4 h-4 accent-destructive"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate text-foreground">
                              {track.title}
                            </div>
                            <div className="text-xs text-muted-foreground truncate">
                              {track.artist}
                            </div>
                          </div>
                          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 bg-destructive/10 text-destructive rounded">
                            Delete
                          </span>
                        </label>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-3 flex items-center gap-2">
                      <CheckCircle size={12} /> Files will be moved to Recycle
                      Bin (safe delete).
                    </p>
                  </div>
                )}
              </div>
            )}

            {step === "executing" && (
              <div className="flex flex-col items-center justify-center h-64 gap-4">
                <div className="relative">
                  <div className="absolute inset-0 bg-destructive/20 rounded-full animate-ping" />
                  <Loader2 className="w-12 h-12 animate-spin text-destructive relative z-10" />
                </div>
                <p className="text-muted-foreground font-medium">
                  Synchronizing library...
                </p>
              </div>
            )}

            {step === "success" && result && (
              <div className="flex flex-col items-center justify-center h-full py-8 text-center space-y-6">
                <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center text-green-500 mb-2">
                  <CheckCircle className="w-10 h-10" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-foreground">
                    Sync Complete
                  </h3>
                  <p className="text-muted-foreground">
                    Your library is now up to date.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4 w-full max-w-sm">
                  <div className="bg-secondary/20 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-foreground">
                      {result.removed_from_playlist}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Removed from Queue
                    </div>
                  </div>
                  <div className="bg-secondary/20 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-foreground">
                      {result.files_soft_deleted}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Files Moved to Trash
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border bg-secondary/10 flex justify-end gap-3">
            {step !== "executing" && (
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg text-muted-foreground hover:text-foreground font-medium text-sm transition-colors"
              >
                {step === "success" ? "Close" : "Cancel"}
              </button>
            )}

            {step === "review" && report && report.to_remove_count > 0 && (
              <button
                onClick={handleExecute}
                disabled={selectedRemovals.length === 0}
                className={cn(
                  "px-4 py-2 rounded-lg text-white font-medium text-sm transition-all shadow-lg flex items-center gap-2",
                  "bg-destructive hover:bg-destructive/90 shadow-destructive/20",
                  selectedRemovals.length === 0 &&
                    "opacity-50 cursor-not-allowed"
                )}
              >
                <Trash2 size={16} />
                Confirm Deletion
              </button>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>,
    document.body
  );
}
