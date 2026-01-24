import { Search as SearchIcon, X, Filter } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "../../hooks/useTranslation";

interface SearchBarProps {
  onSearch: (query: string, source: string, type: string) => void;
  isLoading: boolean;
  initialQuery?: string;
  initialSource?: string;
  initialType?: string;
}

export default function SearchBar({
  onSearch,
  isLoading,
  initialQuery = "",
  initialSource = "all",
  initialType = "all",
}: Readonly<SearchBarProps>) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(initialQuery);
  const [source, setSource] = useState(initialSource);
  const [type, setType] = useState(initialType);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query, source, type);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto mb-12 relative z-10">
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        onSubmit={handleSubmit}
        className="relative flex flex-col md:flex-row items-center gap-4"
      >
        <div className="relative flex-1 w-full">
          <SearchIcon
            className="absolute left-5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
            size={22}
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("search.placeholder")}
            className="w-full pl-14 pr-12 py-5 rounded-2xl bg-card/60 backdrop-blur-xl border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:bg-card/80 transition-all shadow-lg focus:shadow-primary/20 focus:ring-1 focus:ring-primary/50 text-lg"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X size={20} />
            </button>
          )}
        </div>

        <div className="flex gap-4 w-full md:w-auto">
          <div className="relative min-w-35">
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full appearance-none px-6 py-5 rounded-2xl bg-card/60 backdrop-blur-xl border border-border text-foreground font-medium focus:outline-none focus:border-primary/50 cursor-pointer hover:bg-card/80 transition-all"
            >
              <option value="all" className="bg-popover text-popover-foreground">
                {t("filters.allTypes")}
              </option>
              <option value="artist" className="bg-popover text-popover-foreground">
                {t("filters.artists")}
              </option>
              <option value="playlist" className="bg-popover text-popover-foreground">
                {t("filters.playlists")}
              </option>
              <option value="track" className="bg-popover text-popover-foreground">
                {t("filters.tracks")}
              </option>
            </select>
            <Filter
              className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
              size={18}
            />
          </div>

          <div className="relative min-w-35">
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full appearance-none px-6 py-5 rounded-2xl bg-card/60 backdrop-blur-xl border border-border text-foreground font-medium focus:outline-none focus:border-primary/50 cursor-pointer hover:bg-card/80 transition-all"
            >
              <option value="all" className="bg-popover text-popover-foreground">
                {t("filters.allSources")}
              </option>
              <option value="spotify" className="bg-popover text-popover-foreground">
                Spotify
              </option>
              <option value="youtube" className="bg-popover text-popover-foreground">
                YouTube
              </option>
              <option value="deezer" className="bg-popover text-popover-foreground">
                Deezer
              </option>
              <option value="apple_music" className="bg-popover text-popover-foreground">
                Apple Music
              </option>
              <option value="tidal" className="bg-popover text-popover-foreground">
                Tidal
              </option>
              <option value="amazon_music" className="bg-popover text-popover-foreground">
                Amazon Music
              </option>
              <option value="soundcloud" className="bg-popover text-popover-foreground">
                SoundCloud
              </option>
            </select>
            <Filter
              className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
              size={18}
            />
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            type="submit"
            disabled={isLoading}
            className="px-10 py-5 rounded-2xl bg-primary text-primary-foreground font-bold shadow-lg shadow-primary/30 hover:shadow-primary/50 transition-all disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap"
          >
            {isLoading ? t("search.searching") : t("filters.search")}
          </motion.button>
        </div>
      </motion.form>
    </div>
  );
}
