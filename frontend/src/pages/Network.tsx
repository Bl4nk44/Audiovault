import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Shield,
  Server,
  Globe,
  Lock,
  Save,
  RefreshCw,
  Key,
} from "lucide-react";
import api from "../services/api";
import { toast } from "react-hot-toast";
import { useTranslation } from "../hooks/useTranslation";

interface NetworkStatus {
  ip?: string;
  status: "connected" | "error" | "unreachable";
  mode: string;
  error?: string;
}

export default function Network() {
  const { t } = useTranslation();
  const [statuses, setStatuses] = useState<Record<string, NetworkStatus>>({});
  const [loading, setLoading] = useState(false);
  const [wireguardConfig, setWireguardConfig] = useState("");
  const [selectedMode, setSelectedMode] = useState("direct");
  const [showConfig, setShowConfig] = useState(true);

  const checkStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/network/status");
      setStatuses(res.data);

      // Check for errors and notify
      if (selectedMode !== "direct") {
        const currentStatus =
          res.data[selectedMode === "tor_vpn" ? "tor" : selectedMode];

        if (
          currentStatus?.status === "error" ||
          currentStatus?.status === "unreachable"
        ) {
          if (currentStatus.error) {
            toast.error(
              `[${selectedMode.toUpperCase()}] ${currentStatus.error}`,
              { id: `err-${selectedMode}` }
            );
          }
        }
      }
    } catch {
      toast.error(t("network.toasts.statusFailed"));
    } finally {
      setLoading(false);
    }
  }, [selectedMode, t]);

  useEffect(() => {
    checkStatus();
    // Fetch initial config if possible? Or logic to fetch current mode
    // checkMode();
  }, [selectedMode]); // Added dependency to fix lint warning

  const handleSaveConfig = async () => {
    try {
      await api.post("/network/config/wireguard", {
        wireguard_config: wireguardConfig,
      });
      toast.success(t("network.toasts.configSaved"));
      setShowConfig(false);
    } catch {
      toast.error(t("network.toasts.saveFailed"));
    }
  };

  const handleModeChange = async (mode: string) => {
    try {
      await api.post("/network/mode", { mode });
      setSelectedMode(mode);
      toast.success(t("network.toasts.modeChanged").replace("{{mode}}", mode));
    } catch {
      toast.error(t("network.toasts.modeFailed"));
    }
  };

  const modes = [
    {
      id: "direct",
      label: t("network.modes.direct.label"),
      icon: Globe,
      desc: t("network.modes.direct.desc"),
    },
    {
      id: "vpn",
      label: t("network.modes.vpn.label"),
      icon: Lock,
      desc: t("network.modes.vpn.desc"),
    },
    {
      id: "tor",
      label: t("network.modes.tor.label"),
      icon: Shield,
      desc: t("network.modes.tor.desc"),
    },
    {
      id: "tor_vpn",
      label: t("network.modes.tor_vpn.label"),
      icon: Server,
      desc: t("network.modes.tor_vpn.desc"),
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto space-y-8"
    >
      <div className="flex items-center gap-4 mb-8">
        <div className="p-4 bg-primary/20 rounded-2xl text-primary">
          <Shield size={40} />
        </div>
        <div>
          <h1 className="text-4xl font-bold text-white">
            {t("network.title")}
          </h1>
          <p className="text-gray-400 mt-1">{t("network.subtitle")}</p>
        </div>
      </div>

      {/* Connectivity Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {["direct", "vpn", "tor"].map((mode) => {
          const status = statuses[mode];
          const isError =
            status?.status === "error" || status?.status === "unreachable";

          // Simplified messages for cards
          let displayStatus = status?.ip || t("network.status.checking");
          if (isError) {
            if (mode === "vpn") displayStatus = t("network.status.vpnOff");
            else if (mode === "tor") displayStatus = t("network.status.torOff");
            else displayStatus = t("network.status.noConnection");
          }

          // Trigger toast for detailed errors if new error detected
          // (Logic moved to effect or simplified here just for display)
          // We won't trigger toast in render loop, but we hide detailed error from card.

          return (
            <div
              key={mode}
              className={`border p-6 rounded-2xl backdrop-blur-sm transition-all ${
                status?.status === "connected"
                  ? "bg-black/20 border-white/5"
                  : "bg-red-500/5 border-red-500/20"
              }`}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="uppercase text-sm font-bold tracking-wider text-white">
                  {mode === "direct"
                    ? t("network.yourIp")
                    : mode === "vpn"
                    ? t("network.vpnIp")
                    : t("network.torIp")}
                </h3>
                {status?.status === "connected" ? (
                  <div className="w-3 h-3 bg-green-500 rounded-full shadow-[0_0_10px_rgba(34,197,94,0.6)]"></div>
                ) : (
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                )}
              </div>
              <div
                className={`text-2xl font-mono truncate ${
                  isError ? "text-red-400 font-bold text-lg" : "text-white"
                }`}
              >
                {displayStatus}
              </div>

              {/* Detailed error hidden from card, user can see logs or notification */}
            </div>
          );
        })}
      </div>

      <div className="flex justify-end">
        <button
          onClick={checkStatus}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-xl transition-colors text-sm font-bold"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          {t("network.status.refresh")}
        </button>
      </div>

      {/* Mode Selection */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">{t("network.mode")}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {modes.map((m) => (
            <div
              key={m.id}
              onClick={() => handleModeChange(m.id)}
              className={`p-6 rounded-2xl border cursor-pointer transition-all ${
                selectedMode === m.id
                  ? "bg-primary/20 border-primary shadow-[0_0_20px_rgba(var(--primary-rgb),0.2)]"
                  : "bg-black/20 border-white/5 hover:border-white/20"
              }`}
            >
              <div className="flex items-center gap-4">
                <m.icon
                  size={32}
                  className={
                    selectedMode === m.id ? "text-primary" : "text-gray-400"
                  }
                />
                <div>
                  <h3
                    className={`font-bold text-lg ${
                      selectedMode === m.id ? "text-white" : "text-gray-300"
                    }`}
                  >
                    {m.label}
                  </h3>
                  <p className="text-sm text-gray-400">{m.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* WireGuard Config */}
      <div className="bg-black/30 border border-white/10 rounded-2xl p-8 space-y-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-blue-500/20 text-blue-400 rounded-xl">
            <Key size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">
              {t("network.wireguardConfig")}
            </h2>
            <p className="text-gray-400 text-sm mt-1">
              {t("network.wireguardDesc")}
            </p>
          </div>
        </div>

        {showConfig ? (
          <textarea
            value={wireguardConfig}
            onChange={(e) => setWireguardConfig(e.target.value)}
            placeholder="[Interface]
PrivateKey = ...
Address = ...
DNS = ...

[Peer]
PublicKey = ...
Endpoint = ...
AllowedIPs = 0.0.0.0/0
..."
            className="w-full h-64 bg-black/50 border border-white/10 rounded-xl p-4 font-mono text-sm text-gray-300 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50"
          />
        ) : (
          <div className="w-full h-64 bg-black/20 border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center text-center space-y-4">
            <div className="p-4 bg-white/5 rounded-full text-gray-400">
              <Key size={32} />
            </div>
            <p className="text-gray-400 max-w-sm">
              {t("network.configHidden")}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-4">
          {!showConfig && (
            <button
              onClick={() => setShowConfig(true)}
              className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 text-white font-bold rounded-xl transition-all"
            >
              <Key size={20} />
              {t("network.editConfig")}
            </button>
          )}

          {showConfig && (
            <button
              onClick={handleSaveConfig}
              className="flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary/80 text-black font-bold rounded-xl transition-all shadow-lg hover:shadow-primary/25"
            >
              <Save size={20} />
              {t("network.save")}
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
