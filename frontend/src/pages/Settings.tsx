import SettingsPanel from "../components/settings/SettingsPanel";
import { motion } from "framer-motion";
import { useTranslation } from "../hooks/useTranslation";

export default function Settings() {
  const { t } = useTranslation();

  return (
    <div className="relative min-h-screen">
      <div className="relative z-10 space-y-8 p-6">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-2"
        >
          <h1 className="text-4xl font-bold tracking-tight text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">
            {t("common.settings")}
          </h1>
          <p className="text-gray-400 text-lg">{t("settings.subtitle")}</p>
        </motion.div>

        <SettingsPanel />
      </div>
    </div>
  );
}
