import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "../hooks/useTranslation";
import { useSearchParams } from "react-router-dom";
import SearchBar from "../components/search/SearchBar";
import SearchResults from "../components/search/SearchResults";
import api from "../services/api";
import { notify as toast } from "../utils/notify";

// Helper function moved outside component
const detectSourceFromUrl = (query: string): string => {
  const q = query.toLowerCase();
  if (q.includes("spotify.com") || q.includes("spotify:")) return "spotify";
  if (q.includes("youtube.com") || q.includes("youtu.be")) return "youtube";
  if (q.includes("soundcloud.com")) return "soundcloud";
  if (q.includes("music.apple.com")) return "apple_music";
  if (q.includes("listen.tidal.com") || q.includes("tidal.com")) return "tidal";
  if (q.includes("deezer.com")) return "deezer";
  if (q.includes("music.amazon.com") || q.includes("amazon.com/music"))
    return "amazon_music";
  return "all";
};

export default function Search() {
  const [searchParams] = useSearchParams();
   
  const [results, setResults] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [currentQuery, setCurrentQuery] = useState("");
  const [currentSource, setCurrentSource] = useState("all");
  const [currentType, setCurrentType] = useState("all");

  const { t } = useTranslation();

  const fetchResults = async (
    query: string,
    source: string,
    type: string,
    currentOffset: number
  ) => {
     
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

  /* eslint-disable react-hooks/exhaustive-deps */
  const handleSearch = useCallback(
    async (query: string, source: string, type: string) => {
      // Update URL with search params
      const params = new URLSearchParams();
      params.set("q", query);
      if (source !== "all") params.set("source", source);
      if (type !== "all") params.set("type", type);

      // If the URL is already correct, perform the search (happens on load or back nav)
      // Otherwise, navigation will trigger the useEffect below
      if (
        searchParams.get("q") === query &&
        (searchParams.get("source") || "all") === source &&
        (searchParams.get("type") || "all") === type
      ) {
        // Proceed to fetch
      } else {
        // Just update URL, finding will happen in useEffect
        // Replace: false adds to history stack
        // Replace: true would replace current entry
        setSearchParams(params);
        return;
      }

      setIsLoading(true);
      setResults([]);
      setOffset(0);
      setHasMore(true);

      // Auto-detect source and type from URL (logic moved to helper)
      let effectiveSource = source;
      // If user selected "all" but we can detect a specific source from the URL/Query, use it
      if (source === "all") {
        effectiveSource = detectSourceFromUrl(query);
      }

      const effectiveType = type;

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
    },
    [searchParams] // Re-create when params change
  );

  const setSearchParams = useSearchParams()[1];

  useEffect(() => {
    const queryParam = searchParams.get("q");
    const sourceParam = searchParams.get("source") || "all";
    const typeParam = searchParams.get("type") || "all";

    if (queryParam) {
      // Only trigger if it's different (to avoid loop, though useCallback deps handle it)
      if (
        queryParam !== currentQuery ||
        sourceParam !== currentSource ||
        typeParam !== currentType
      ) {

        handleSearch(
          queryParam,
          sourceParam,
          typeParam
        );
      }
    }
  }, [searchParams]);

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

      <SearchBar
        key={`${currentQuery}-${currentSource}-${currentType}`}
        onSearch={handleSearch}
        isLoading={isLoading}
        initialQuery={currentQuery}
        initialSource={currentSource}
        initialType={currentType}
      />

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
