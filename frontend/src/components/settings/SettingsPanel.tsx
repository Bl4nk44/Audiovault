import { useEffect, useState } from "react";

import { motion } from "framer-motion";
import { Download, FileText, FolderOpen, Globe, Palette, Save, User, UserPlus } from "lucide-react";
import { useTranslation } from "../../hooks/useTranslation";
import api from "../../services/api";
import { setRegistrationEnabled as apiSetRegistration } from "../../services/auth";
import { useStore } from "../../store/useStore";
import { notify as toast } from "../../utils/notify";
import AccountSettings from "./AccountSettings";

export default function SettingsPanel() {
  const { t } = useTranslation();
  const updateUserPreferences = useStore((state) => state.updateUserPreferences);
  const isAdmin = useStore((state) => state.user?.is_admin === true);
  const [activeTab, setActiveTab] = useState("general");
  const [registrationEnabled, setRegistrationEnabled] = useState(true);
  const [settings, setSettings] = useState({
    spotifyClientId: "",
    spotifyClientSecret: "",
    youtubeApiKey: "",
    deezerApiKey: "",
    downloadPath: "/downloads",
    maxParallelDownloads: 3,
    theme: "dark",
    language: "en",
    filenameSchema: "{artist} - {title}",
    audioQuality: "high",
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // fetchSettings defined below; intentional effect-driven fetch (pre-TanStack pattern)
    // eslint-disable-next-line react-hooks/immutability
    fetchSettings();
  }, []);

  // Apply theme immediately on change for preview
  useEffect(() => {
    document.documentElement.className = settings.theme;
  }, [settings.theme]);

  const fetchSettings = async () => {
    try {
      const response = await api.get("/settings/");
      setSettings((prev) => ({ ...prev, ...response.data }));
      if (isAdmin) {
        const reg = await api.get("/settings/registration");
        setRegistrationEnabled(reg.data.enabled);
      }
    } catch (error) {
      console.error("Failed to fetch settings:", error);
      toast.error(t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  const handleToggleRegistration = async () => {
    const next = !registrationEnabled;
    try {
      await apiSetRegistration(next);
      setRegistrationEnabled(next);
      toast.success(t("common.saved"));
    } catch (error) {
      console.error("Failed to update registration setting:", error);
      toast.error(t("common.error"));
    }
  };

  const handleSave = async () => {
    try {
      await api.post("/settings/", settings);
      updateUserPreferences(settings);
      toast.success(t("common.saved"));
    } catch (error) {
      console.error("Failed to save settings:", error);
      toast.error(t("common.error"));
    }
  };

  const tabs = [
    { id: "general", label: t("settings.general"), icon: Globe },
    { id: "account", label: t("settings.account"), icon: User },
    { id: "appearance", label: t("settings.appearance"), icon: Palette },
    { id: "files", label: t("settings.files"), icon: FileText },
  ];

  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } },
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  };

  if (loading) return <div className="text-white text-center py-10">{t("common.loading")}</div>;

  return (
    <div className="flex flex-col md:flex-row gap-8 pb-20 max-w-6xl">
      {/* Sidebar Tabs */}
      <div className="w-full md:w-64 shrink-0 space-y-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all cursor-pointer ${
              activeTab === tab.id
                ? "bg-primary text-primary-foreground font-bold shadow-[0_0_15px_hsl(var(--primary)/0.4)]"
                : "text-muted-foreground hover:text-foreground hover:bg-white/5"
            }`}
          >
            <tab.icon size={18} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <motion.div
        key={activeTab}
        variants={container}
        initial="hidden"
        animate="show"
        className="flex-1 space-y-6"
      >
        {activeTab === "account" && <AccountSettings />}

        {activeTab === "general" && (
          <motion.div variants={item} className="space-y-6 p-8 rounded-(--radius) glass">
            <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4">
              {t("settings.general")}
            </h3>

            <div className="grid gap-6">
              <div className="space-y-2">
                <label className="text-sm font-medium text-muted-foreground ml-1">
                  {t("settings.language")}
                </label>
                <div className="relative">
                  <select
                    value={settings.language}
                    onChange={(e) => setSettings({ ...settings, language: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-secondary/50 border border-border text-foreground focus:outline-none focus:border-primary/50 appearance-none cursor-pointer"
                  >
                    <option value="en" className="bg-popover text-popover-foreground">
                      English
                    </option>
                    <option value="pl" className="bg-popover text-popover-foreground">
                      Polski
                    </option>
                    <option value="de" className="bg-popover text-popover-foreground">
                      Deutsch
                    </option>
                    <option value="fr" className="bg-popover text-popover-foreground">
                      Français
                    </option>
                    <option value="es" className="bg-popover text-popover-foreground">
                      Español
                    </option>
                  </select>
                  {/* Custom Arrow Icon */}
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-white/50">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300 ml-1">
                  {t("settings.audioQuality")}
                </label>
                <div className="relative">
                  <select
                    value={settings.audioQuality}
                    onChange={(e) => setSettings({ ...settings, audioQuality: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-secondary/50 border border-white/10 text-white focus:outline-none focus:border-primary/50 appearance-none cursor-pointer"
                  >
                    <option value="low" className="bg-popover text-popover-foreground">
                      {t("quality.low")}
                    </option>
                    <option value="normal" className="bg-popover text-popover-foreground">
                      {t("quality.normal")}
                    </option>
                    <option value="high" className="bg-popover text-popover-foreground">
                      {t("quality.high")}
                    </option>
                    <option value="lossless" className="bg-popover text-popover-foreground">
                      {t("quality.lossless")}
                    </option>
                  </select>
                  {/* Custom Arrow Icon */}
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-white/50">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300 ml-1 flex items-center gap-2">
                  <Download size={16} /> {t("settings.maxDownloads")}
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={settings.maxParallelDownloads}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      maxParallelDownloads: Number.parseInt(e.target.value),
                    })
                  }
                  className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                />
              </div>

              {isAdmin && (
                <div className="flex items-center justify-between gap-4 pt-2 border-t border-white/10">
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-muted-foreground ml-1 flex items-center gap-2">
                      <UserPlus size={16} /> {t("settings.registration")}
                    </label>
                    <p className="text-xs text-gray-500 ml-1">{t("settings.registrationDesc")}</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={registrationEnabled}
                    onClick={handleToggleRegistration}
                    className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors cursor-pointer ${
                      registrationEnabled ? "bg-primary" : "bg-gray-600"
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        registrationEnabled ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === "appearance" && (
          <motion.div variants={item} className="space-y-6 p-8 rounded-(--radius) glass">
            <h3 className="text-xl font-bold text-foreground border-b border-border pb-4">
              {t("settings.appearance")}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                {
                  id: "dark",
                  name: t("settings.themes.dark"),
                  color: "bg-[#09090b]",
                },
                {
                  id: "midnight",
                  name: t("settings.themes.midnight"),
                  color: "bg-[#1e1b4b]", // Indigo 950
                },
                {
                  id: "ocean",
                  name: t("settings.themes.ocean"),
                  color: "bg-[#083344]", // Cyan 950
                },
                {
                  id: "forest",
                  name: t("settings.themes.forest"),
                  color: "bg-[#052e16]",
                },
                {
                  id: "sunset",
                  name: t("settings.themes.sunset"),
                  color: "bg-[#450a0a]",
                },
                {
                  id: "neon",
                  name: t("settings.themes.neon"),
                  color: "bg-[#ff00aa]", // Neon Pink
                },
              ].map((theme) => (
                <button
                  key={theme.id}
                  onClick={() => setSettings({ ...settings, theme: theme.id })}
                  className={`relative p-4 rounded-2xl border-2 transition-all overflow-hidden group cursor-pointer ${
                    settings.theme === theme.id
                      ? "border-primary shadow-[0_0_20px_hsl(var(--primary)/0.2)]"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <div className={`absolute inset-0 ${theme.color} opacity-80`} />
                  <div className="relative z-10 flex flex-col items-center gap-2">
                    <div className="w-full h-12 rounded-lg bg-card/10 backdrop-blur-sm border border-white/10" />
                    <span className="font-medium text-white shadow-black drop-shadow-md">
                      {theme.name}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === "files" && (
          <motion.div variants={item} className="space-y-6 p-8 rounded-(--radius) glass">
            <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4">
              {t("settings.files")}
            </h3>

            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300 ml-1 flex items-center gap-2">
                  <FolderOpen size={16} /> {t("settings.downloadPath")}
                </label>
                <input
                  type="text"
                  value={settings.downloadPath}
                  onChange={(e) => setSettings({ ...settings, downloadPath: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300 ml-1 flex items-center gap-2">
                  <FileText size={16} /> {t("settings.filenameSchema")}
                </label>
                <input
                  type="text"
                  value={settings.filenameSchema}
                  onChange={(e) => setSettings({ ...settings, filenameSchema: e.target.value })}
                  className="w-full bg-black/40 border border-white/10 rounded-(--radius) p-3 text-white focus:outline-none focus:border-primary/50 transition-colors text-sm"
                  placeholder="{user}/{service}/{playlist}/{artist} - {title}"
                />
                <p className="text-xs text-gray-500 ml-1 leading-relaxed">
                  {t("settings.availableTags")} <code className="text-primary">{"{artist}"}</code>,{" "}
                  <code className="text-primary">{"{title}"}</code>,{" "}
                  <code className="text-primary">{"{album}"}</code>,{" "}
                  <code className="text-primary">{"{id}"}</code>,{" "}
                  <code className="text-primary">{"{year}"}</code>,{" "}
                  <code className="text-primary">{"{track_number}"}</code>,{" "}
                  <code className="text-primary">{"{playlist}"}</code>,{" "}
                  <code className="text-primary">{"{service}"}</code>,{" "}
                  <code className="text-primary">{"{user}"}</code>
                  <br />
                  Use <code className="text-primary">/</code> to create folders (e.g.{" "}
                  <code className="text-gray-300">
                    {"{user}/{service}/{playlist}/{artist} - {title}"}
                  </code>
                  {" )"}
                </p>

                <div className="mt-2 p-3 rounded-lg bg-black/30 border border-white/5 text-sm text-gray-400 font-mono">
                  <span className="text-gray-500 uppercase text-xs font-bold mr-2 block mb-1 font-sans">
                    {t("settings.preview")}
                  </span>
                  <div className="flex items-center gap-2">
                    <FolderOpen size={14} className="text-yellow-500" />
                    <span>{settings.downloadPath}</span>
                  </div>
                  {settings.filenameSchema.split("/").map((part, index, array) => (
                    <div
                      key={part + index}
                      className="flex items-center gap-2 ml-4 border-l border-white/10 pl-2"
                    >
                      {index === array.length - 1 ? (
                        <FileText size={14} className="text-blue-400" />
                      ) : (
                        <FolderOpen size={14} className="text-yellow-500" />
                      )}
                      <span>
                        {part
                          .replace("{artist}", "The Weeknd")
                          .replace("{title}", "Blinding Lights")
                          .replace("{album}", "After Hours")
                          .replace("{id}", "12345")
                          .replace("{year}", "2020")
                          .replace("{track_number}", "01")
                          .replace("{playlist}", "Top Hits")
                          .replace("{service}", "spotify")
                          .replace("{user}", "admin")}
                        {index === array.length - 1 ? ".mp3" : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        <motion.div variants={item} className="flex justify-end pt-4">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSave}
            className="flex items-center gap-2 bg-primary text-black font-bold px-8 py-4 rounded-xl shadow-[0_0_20px_rgba(34,197,94,0.3)] hover:shadow-[0_0_30px_rgba(34,197,94,0.5)] transition-all cursor-pointer"
          >
            <Save size={20} />
            {t("common.save")}
          </motion.button>
        </motion.div>
      </motion.div>
    </div>
  );
}
