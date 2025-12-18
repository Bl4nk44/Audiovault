import { useState } from "react";
import { useTranslation } from "../hooks/useTranslation";
import SearchBar from "../components/search/SearchBar";
import SearchResults from "../components/search/SearchResults";
import api from "../services/api";
import toast from "react-hot-toast";

export default function Search() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [currentQuery, setCurrentQuery] = useState("");
  const [currentSource, setCurrentSource] = useState("all");
  const [currentType, setCurrentType] = useState("all");

  const { t } = useTranslation();

  const handleSearch = async (query: string, source: string, type: string) => {
    setIsLoading(true);
    setResults([]);
    setOffset(0);
    setHasMore(true);

    // Auto-detect source and type from URL
    let effectiveSource = source;
    const effectiveType = type;

    if (query.includes("spotify.com") || query.includes("spotify:")) {
      effectiveSource = "spotify";
    } else if (query.includes("youtube.com") || query.includes("youtu.be")) {
      effectiveSource = "youtube";
    }

    setCurrentQuery(query);
    setCurrentSource(effectiveSource);
    setCurrentType(effectiveType);

    try {
      await fetchResults(query, effectiveSource, effectiveType, 0);
    } catch (error) {
      toast.error("Search failed");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchResults = async (
    query: string,
    source: string,
    type: string,
    currentOffset: number
  ) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let newResults: any[] = [];

    // Determine which types to fetch
    let typesToFetch = ["track", "artist", "playlist"];
    if (type !== "all") {
      typesToFetch = [type];
    }

    if (source === "spotify") {
      // Spotify supports multiple types in one call
      try {
        const spotifyTypes = type === "all" ? "track,artist,playlist" : type;
        const response = await api.get("/spotify/search", {
          params: { q: query, offset: currentOffset, type: spotifyTypes },
        });
        newResults = response.data;
      } catch (e) {
        console.error(e);
      }
    } else if (source === "youtube") {
      // YouTube needs separate calls
      const promises = typesToFetch.map((t) =>
        api
          .get("/youtube/search", {
            params: { q: query, offset: currentOffset, type: t },
          })
          .then((res) => res.data)
          .catch(() => [])
      );
      const results = await Promise.all(promises);
      newResults = results.flat();
    } else if (source === "all") {
      // Fetch from all sources
      const spotifyTypes = type === "all" ? "track,artist,playlist" : type;
      const spotifyPromise = api
        .get("/spotify/search", {
          params: { q: query, offset: currentOffset, type: spotifyTypes },
        })
        .then((res) => res.data)
        .catch(() => []);

      const youtubePromises = typesToFetch.map((t) =>
        api
          .get("/youtube/search", {
            params: { q: query, offset: currentOffset, type: t },
          })
          .then((res) => res.data)
          .catch(() => [])
      );

      // Deezer (tracks only for now)
      // Only fetch deezer if type is 'all' or 'track'
      let deezerPromise = Promise.resolve([]);
      if (type === "all" || type === "track") {
        deezerPromise = api
          .get("/deezer/search", {
            params: { q: query, offset: currentOffset },
          })
          .then((res) => res.data)
          .catch(() => []);
      }

      const [spotifyResults, ...youtubeResultsArray] = await Promise.all([
        spotifyPromise,
        ...youtubePromises,
        deezerPromise,
      ]);
      const deezerResults = youtubeResultsArray.pop(); // Last one is deezer

      newResults = [
        ...spotifyResults,
        ...youtubeResultsArray.flat(),
        ...deezerResults,
      ];
    } else {
      // Fallback for other sources (deezer, apple_music, tidal, amazon_music)
      const response = await api.get(`/${source}/search`, {
        params: { q: query, offset: currentOffset },
      });
      newResults = response.data;
    }

    if (newResults.length === 0) {
      setHasMore(false);
    } else {
      setResults((prev) =>
        currentOffset === 0 ? newResults : [...prev, ...newResults]
      );
      setOffset(currentOffset + 20);
    }
  };

  const handleLoadMore = async () => {
    if (isLoading || !hasMore) return;
    setIsLoading(true);
    try {
      // Use the tracked source and type for pagination
      await fetchResults(currentQuery, currentSource, currentType, offset);
    } catch {
      toast.error("Failed to load more");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">
          {t("search.title")}
        </h1>
        <p className="text-muted-foreground">{t("search.subtitle")}</p>
      </div>

      <SearchBar onSearch={handleSearch} isLoading={isLoading} />

      <div className="mt-8 space-y-8">
        <SearchResults
          results={results}
          isLoading={isLoading && offset === 0}
        />

        {results.length > 0 && hasMore && (
          <div className="flex justify-center pb-20">
            <button
              onClick={handleLoadMore}
              disabled={isLoading}
              className="px-8 py-3 rounded-full bg-white/10 hover:bg-white/20 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? t("common.loading") : t("search.loadMore")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
