import { useState, useEffect } from "react";
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

interface NetworkStatus {
  ip?: string;
  status: "connected" | "error" | "unreachable";
  mode: string;
  error?: string;
}

export default function Network() {
  const [statuses, setStatuses] = useState<Record<string, NetworkStatus>>({});
  const [loading, setLoading] = useState(false);
  const [wireguardConfig, setWireguardConfig] = useState("");
  const [selectedMode, setSelectedMode] = useState("direct");

  const checkStatus = async () => {
    setLoading(true);
    try {
      const res = await api.get("/network/status");
      setStatuses(res.data);
    } catch {
      toast.error("Failed to fetch network status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
    // Fetch initial config if possible? Or logic to fetch current mode
    // checkMode();
  }, []);

  const handleSaveConfig = async () => {
    try {
      await api.post("/network/config/wireguard", {
        wireguard_config: wireguardConfig,
      });
      toast.success("Configuration saved. Please restart the VPN container.");
    } catch {
      toast.error("Failed to save configuration");
    }
  };

  const handleModeChange = async (mode: string) => {
    try {
      await api.post("/network/mode", { mode });
      setSelectedMode(mode);
      toast.success(`Network mode changed to ${mode}`);
    } catch {
      toast.error("Failed to update network mode");
    }
  };

  const modes = [
    {
      id: "direct",
      label: "Direct (Bezpośrednie)",
      icon: Globe,
      desc: "Standardowe połączenie, brak anonimowości.",
    },
    {
      id: "vpn",
      label: "WireGuard VPN",
      icon: Lock,
      desc: "Zmiana IP, szyfrowanie, omijanie blokad.",
    },
    {
      id: "tor",
      label: "Tor Network",
      icon: Shield,
      desc: "Wysoka anonimowość, wolniejsze działanie.",
    },
    {
      id: "tor_vpn",
      label: "Tor over VPN",
      icon: Server,
      desc: "Maksymalna ochrona: Tor tunelowany przez VPN.",
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
          <h1 className="text-4xl font-bold text-white">Ochrona Sieci</h1>
          <p className="text-gray-400 mt-1">
            Konfiguracja VPN, Tor i trybów prywatności
          </p>
        </div>
      </div>

      {/* Connectivity Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {["direct", "vpn", "tor"].map((mode) => {
          const status = statuses[mode];
          return (
            <div
              key={mode}
              className="bg-black/20 border border-white/5 p-6 rounded-2xl backdrop-blur-sm"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="uppercase text-sm font-bold tracking-wider text-white">
                  {mode === "direct"
                    ? "Twoje IP"
                    : mode === "vpn"
                    ? "VPN IP"
                    : "Tor IP"}
                </h3>
                {status?.status === "connected" ? (
                  <div className="w-3 h-3 bg-green-500 rounded-full shadow-[0_0_10px_rgba(34,197,94,0.6)]"></div>
                ) : (
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                )}
              </div>
              <div className="text-2xl font-mono text-white truncate">
                {status?.ip || "Sprawdzanie..."}
              </div>
              {status?.error && (
                <p className="text-xs text-red-400 mt-2">{status.error}</p>
              )}
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
          Odśwież Status
        </button>
      </div>

      {/* Mode Selection */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">Tryb Pracy</h2>
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
              Konfiguracja WireGuard
            </h2>
            <p className="text-gray-400 text-sm mt-1">
              Wklej tutaj zawartość swojego pliku konfiguracyjnego (np.{" "}
              <code>wg0.conf</code>). Po zapisaniu wymagany jest restart
              kontenera VPN.
            </p>
          </div>
        </div>

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

        <div className="flex justify-end">
          <button
            onClick={handleSaveConfig}
            className="flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary/80 text-black font-bold rounded-xl transition-all shadow-lg hover:shadow-primary/25"
          >
            <Save size={20} />
            Zapisz Konfigurację
          </button>
        </div>
      </div>
    </motion.div>
  );
}
