import { motion } from "framer-motion";
import { AlertCircle, Download, Pause, Play, RefreshCw, Terminal, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "../hooks/useTranslation";
import api from "../services/api";

export default function Logs() {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<string[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showErrorsOnly, setShowErrorsOnly] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      const res = await api.get<string[]>("/system/logs?lines=500");
      if (Array.isArray(res.data)) {
        setLogs(res.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const downloadLogs = async () => {
    try {
      const response = await api.get("/system/logs/download", {
        responseType: "blob",
      });
      const url = globalThis.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "audiovault.log");
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error("Failed to download logs", error);
    }
  };

  useEffect(() => {
    if (!autoRefresh) return;

    // Initial + polled log fetch from the backend (external system) — belongs in an effect
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  useEffect(() => {
    if (autoRefresh && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoRefresh]);

  const getLogColor = (line: string) => {
    if (line.includes("ERROR") || line.includes("CRITICAL")) return "text-red-400 font-bold";
    if (line.includes("WARNING") || line.includes("WARN")) return "text-yellow-400";
    if (line.includes("INFO")) return "text-blue-400";
    if (line.includes("DEBUG")) return "text-gray-500";
    return "text-gray-300";
  };

  return (
    <div className="h-full flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Terminal className="text-primary" size={32} />
            {t("logs.title")}
          </h1>
          <p className="text-muted-foreground mt-1">{t("logs.subtitle")}</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setShowErrorsOnly(!showErrorsOnly)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors border cursor-pointer ${
              showErrorsOnly
                ? "bg-red-500/20 text-red-500 border-red-500/50"
                : "bg-secondary text-muted-foreground border-transparent hover:text-foreground"
            }`}
          >
            <AlertCircle size={18} />
            {t("logs.showErrorsOnly") || "Errors Only"}
          </button>

          <button
            onClick={downloadLogs}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary text-muted-foreground hover:text-foreground transition-colors border border-transparent hover:border-border cursor-pointer"
          >
            <Download size={18} />
            {t("logs.download")}
          </button>

          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors border cursor-pointer ${
              autoRefresh
                ? "bg-primary/20 text-primary border-primary/50"
                : "bg-secondary text-muted-foreground border-transparent hover:text-foreground"
            }`}
          >
            {autoRefresh ? <Pause size={18} /> : <Play size={18} />}
            {t("logs.autoRefresh")}
          </button>

          <button
            onClick={fetchLogs}
            disabled={autoRefresh || isLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50 border border-transparent hover:border-border cursor-pointer"
          >
            <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
            {t("logs.refresh")}
          </button>

          <button
            onClick={() => setLogs([])}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 transition-colors cursor-pointer"
          >
            <Trash2 size={18} />
            {t("logs.clear")}
          </button>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-1 bg-black/80 backdrop-blur-md rounded-xl border border-white/10 shadow-2xl overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/5 text-xs text-muted-foreground font-mono">
          <span>terminal</span>
          <span>
            {logs.length} {t("logs.lines")}
          </span>
        </div>
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1 custom-scrollbar"
        >
          {logs.length === 0 ? (
            <div className="text-center text-muted-foreground italic pt-10">
              No logs available...
            </div>
          ) : (
            logs
              .filter((line) =>
                showErrorsOnly ? line.includes("ERROR") || line.includes("CRITICAL") : true
              )
              .map((line, i) => (
                <div
                  key={`${i}-${line.substring(0, 10)}`} // Using combination of index and content prefix for better uniqueness
                  className={`whitespace-pre-wrap break-all ${getLogColor(line)}`}
                >
                  <span className="opacity-30 mr-4 select-none">{i + 1}</span>
                  {line}
                </div>
              ))
          )}
        </div>
      </motion.div>
    </div>
  );
}
