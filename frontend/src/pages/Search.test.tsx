import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import api from "../services/api";
import { notify } from "../utils/notify";
import Search from "./Search";

// Mock dependencies
vi.mock("../services/api");
vi.mock("../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("../components/search/SearchResults", () => ({
  default: ({ results, isLoading }: any) => (
    <div data-testid="search-results">
      {isLoading && <div>Loading...</div>}
      {results.map((r: any) => (
        <div key={r.id} data-testid="result-item">
          {r.title}
        </div>
      ))}
    </div>
  ),
}));

vi.mock("../components/search/SearchBar", () => ({
  default: ({ onSearch, initialQuery }: any) => {
    return (
      <div data-testid="search-bar">
        <input data-testid="search-input" defaultValue={initialQuery} onChange={() => {}} />
        <button data-testid="search-btn" onClick={() => onSearch("test query", "spotify", "track")}>
          Search Spotify
        </button>
        <button data-testid="search-all-btn" onClick={() => onSearch("test query", "all", "all")}>
          Search All
        </button>
        <button
          data-testid="search-error-btn"
          onClick={() => onSearch("test query", "soundcloud", "track")}
        >
          Search Soundcloud
        </button>
      </div>
    );
  },
}));

describe("Search Page Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as unknown as Mock).mockResolvedValue({ data: [] });
  });

  const renderSearch = (initialEntry = "/search") => {
    return render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Search />
      </MemoryRouter>
    );
  };

  it("renders search page structure", () => {
    renderSearch();
    expect(screen.getByText("search.title")).toBeInTheDocument();
    expect(screen.getByTestId("search-bar")).toBeInTheDocument();
  });

  it("handles basic Spotify search", async () => {
    (api.get as unknown as Mock).mockResolvedValue({
      data: [{ id: "1", title: "Spotify Song" }],
    });

    renderSearch();
    fireEvent.click(screen.getByTestId("search-btn"));

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/browse/search",
        expect.objectContaining({
          params: expect.objectContaining({ q: "test query", type: "track" }),
        })
      );
      expect(screen.getByText("Spotify Song")).toBeInTheDocument();
    });
  });

  it("handles 'All' source search (Unified API)", async () => {
    (api.get as unknown as Mock).mockImplementation((url) => {
      if (url.includes("browse"))
        return Promise.resolve({ data: [{ id: "b1", title: "Browse Item" }] });
      return Promise.resolve({ data: [] });
    });

    renderSearch();
    fireEvent.click(screen.getByTestId("search-all-btn"));

    await waitFor(() => {
      expect(screen.getAllByText("Browse Item").length).toBe(3);
    });
  });

  it("fetches playlists alongside tracks and artists for type=all", async () => {
    (api.get as unknown as Mock).mockResolvedValue({ data: [] });

    renderSearch();
    fireEvent.click(screen.getByTestId("search-all-btn"));

    await waitFor(() => {
      const calledTypes = (api.get as unknown as Mock).mock.calls
        .filter(([url]) => url === "/browse/search")
        .map(([, config]) => config.params.type);
      expect(calledTypes).toEqual(expect.arrayContaining(["track", "artist", "playlist"]));
    });
  });

  it("does not re-fetch artists and playlists on load more", async () => {
    (api.get as unknown as Mock).mockImplementation((url, config) => {
      if (url === "/browse/search" && config?.params?.type === "track") {
        return Promise.resolve({
          data: Array(20)
            .fill(null)
            .map((_, i) => ({ id: `p${i}`, title: `Result ${i}` })),
        });
      }
      return Promise.resolve({ data: [] });
    });

    renderSearch();
    fireEvent.click(screen.getByTestId("search-all-btn"));

    await waitFor(() => expect(screen.getByText("Result 0")).toBeInTheDocument());

    (api.get as unknown as Mock).mockClear();
    (api.get as unknown as Mock).mockResolvedValue({
      data: [{ id: "p20", title: "Result 20" }],
    });

    const loadMoreBtn = screen.getByText("search.loadMore");
    fireEvent.click(loadMoreBtn);

    await waitFor(() => {
      expect(screen.getByText("Result 20")).toBeInTheDocument();
    });

    const callsAfterLoadMore = (api.get as unknown as Mock).mock.calls.filter(
      ([url]) => url === "/browse/search"
    );
    expect(callsAfterLoadMore).toHaveLength(1);
    expect(callsAfterLoadMore[0][1].params).toEqual(
      expect.objectContaining({ type: "track", offset: 20 })
    );
  });

  it("initializes from URL and performs auto-search", async () => {
    (api.get as unknown as Mock).mockResolvedValue({
      data: [{ id: "u1", title: "URL Param Result" }],
    });

    renderSearch("/search?q=hello&source=spotify&type=track");

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/browse/search",
        expect.objectContaining({ params: expect.objectContaining({ q: "hello" }) })
      );
      expect(screen.getByText("URL Param Result")).toBeInTheDocument();
    });
  });

  it("handles pagination (Load More)", async () => {
    (api.get as unknown as Mock).mockResolvedValue({
      data: Array(20)
        .fill(null)
        .map((_, i) => ({ id: `p${i}`, title: `Result ${i}` })),
    });

    renderSearch();
    fireEvent.click(screen.getByTestId("search-btn"));

    await waitFor(() => expect(screen.getByText("Result 0")).toBeInTheDocument());

    const loadMoreBtn = screen.getByText("search.loadMore");
    (api.get as unknown as Mock).mockResolvedValue({
      data: [{ id: "p20", title: "Result 20" }],
    });

    fireEvent.click(loadMoreBtn);

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledTimes(2);
      expect(screen.getByText("Result 20")).toBeInTheDocument();
    });
  });

  it("handles search errors gracefully", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    (api.get as unknown as Mock).mockRejectedValue(new Error("API Fail"));

    renderSearch();
    // Click Soundcloud button which bypasses simplified validation/swallowing
    fireEvent.click(screen.getByTestId("search-error-btn"));

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Search failed");
    });
    spy.mockRestore();
  });

  it("handles failure in 'All' search gracefully", async () => {
    (api.get as unknown as Mock).mockRejectedValue(new Error("API Fail"));

    renderSearch();
    fireEvent.click(screen.getByTestId("search-all-btn"));

    await waitFor(() => {
      // Should handle the error and maybe not crash
      expect(screen.queryByTestId("result-item")).not.toBeInTheDocument();
    });
  });

  it("handles empty results and disables load more", async () => {
    (api.get as unknown as Mock).mockResolvedValue({ data: [] });

    renderSearch();
    fireEvent.click(screen.getByTestId("search-btn"));

    await waitFor(() => {
      // API called
      expect(api.get).toHaveBeenCalled();
      // No results (implied by mocked SearchResults or lack of items)
    });

    // Load more button should NOT be present if hasMore is false
    // Implementation: if (newResults.length === 0) setHasMore(false)
    await waitFor(() => {
      expect(screen.queryByText("search.loadMore")).not.toBeInTheDocument();
    });
  });

  it("handles load more error", async () => {
    // First search succeeds
    (api.get as unknown as Mock).mockResolvedValueOnce({
      data: [{ id: "p1", title: "Res 1" }],
    });

    renderSearch();
    // Use soundcloud button which maps to a source that throws errors (unlike spotify which swallows them)
    fireEvent.click(screen.getByTestId("search-error-btn"));
    await waitFor(() => expect(screen.getByText("Res 1")).toBeInTheDocument());

    // Load more fails
    const loadMoreBtn = screen.getByText("search.loadMore");
    (api.get as unknown as Mock).mockRejectedValueOnce(new Error("Load more fail"));

    fireEvent.click(loadMoreBtn);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to load more");
    });
  });
});
