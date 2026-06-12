import { Activity, ArrowDown, ArrowUp, Cpu, HardDrive, Server } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import api from "../../services/api";
import Gauge from "./Gauge";

type SystemStats = {
  cpu: { percent: number };
  memory: { total: number; used: number; percent: number };
  disk: { total: number; used: number; percent: number };
  network: { sent: number; recv: number };
};

type NetworkSpeed = {
  downBps: number;
  upBps: number;
};

const formatBytes = (bytes: number, decimals = 2) => {
  if (!+bytes) return "0 B";
  const k = 1024;
  const dm = Math.max(decimals, 0);
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Number.parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

const formatSpeed = (bps: number) => {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} KB/s`;
  if (bps < 1024 * 1024 * 1024) return `${(bps / (1024 * 1024)).toFixed(2)} MB/s`;
  return `${(bps / (1024 * 1024 * 1024)).toFixed(2)} GB/s`;
};

export default function SystemStats() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [speed, setSpeed] = useState<NetworkSpeed>({ downBps: 0, upBps: 0 });
  const prevRef = useRef<{ recv: number; sent: number; ts: number } | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get("/system/stats");
        const data: SystemStats = response.data;
        const now = Date.now();

        if (prevRef.current !== null) {
          const dt = (now - prevRef.current.ts) / 1000;
          if (dt > 0) {
            setSpeed({
              downBps: Math.max(0, (data.network.recv - prevRef.current.recv) / dt),
              upBps: Math.max(0, (data.network.sent - prevRef.current.sent) / dt),
            });
          }
        }

        prevRef.current = { recv: data.network.recv, sent: data.network.sent, ts: now };
        setStats(data);
      } catch {
        // Transient polling failure — ignore and retry on next interval
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) {
    // Skeleton or loading state
    return (
      <div className="bg-white/5 border border-white/5 rounded-3xl p-6 backdrop-blur-xl animate-pulse min-h-[300px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-muted rounded-lg w-10 h-10"></div>
          <div className="h-6 bg-muted rounded w-40"></div>
        </div>
        <div className="flex justify-around items-center h-40">
          <div className="w-40 h-20 bg-muted rounded-t-full opacity-20"></div>
          <div className="w-40 h-20 bg-muted rounded-t-full opacity-20"></div>
          <div className="w-40 h-20 bg-muted rounded-t-full opacity-20"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/5 border border-white/5 rounded-3xl p-6 backdrop-blur-xl h-full flex flex-col">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/20 rounded-lg">
          <Server className="w-5 h-5 text-primary" />
        </div>
        <h2 className="text-xl font-bold text-white">System Status</h2>
      </div>

      <div className="flex flex-col gap-8 flex-1 justify-center">
        {/* Gauges Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 justify-items-center">
          <Gauge
            value={stats.cpu.percent}
            label="CPU Load"
            color="text-blue-500"
            icon={<Cpu size={20} />}
          />
          <Gauge
            value={stats.memory.percent}
            label="Memory"
            subLabel={`${formatBytes(stats.memory.used)} / ${formatBytes(stats.memory.total)}`}
            color="text-purple-500"
            icon={<Activity size={20} />}
          />
          <Gauge
            value={stats.disk.percent}
            label="Storage"
            subLabel={`${formatBytes(stats.disk.used)} / ${formatBytes(stats.disk.total)}`}
            color="text-green-500"
            icon={<HardDrive size={20} />}
          />
        </div>

        {/* Network Stats - Compact Row */}
        <div className="bg-black/20 rounded-xl p-4 flex justify-around items-center border border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/10 rounded-full">
              <ArrowDown className="w-5 h-5 text-green-400" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                Download
              </span>
              <span className="text-lg font-bold text-white font-mono">
                {formatSpeed(speed.downBps)}
              </span>
              <span className="text-xs text-gray-500 font-mono">
                {formatBytes(stats.network.recv)} total
              </span>
            </div>
          </div>

          <div className="w-px h-10 bg-white/10"></div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-full">
              <ArrowUp className="w-5 h-5 text-blue-400" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                Upload
              </span>
              <span className="text-lg font-bold text-white font-mono">
                {formatSpeed(speed.upBps)}
              </span>
              <span className="text-xs text-gray-500 font-mono">
                {formatBytes(stats.network.sent)} total
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
