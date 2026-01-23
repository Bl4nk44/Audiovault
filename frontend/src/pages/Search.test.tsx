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
        "/spotify/search",
        expect.objectContaining({
          params: expect.objectContaining({ q: "test query", type: "track" }),
        })
      );
      expect(screen.getByText("Spotify Song")).toBeInTheDocument();
    });
  });

  it("handles 'All' source search (Multiple APIs)", async () => {
    (api.get as unknown as Mock).mockImplementation((url) => {
      if (url.includes("spotify"))
        return Promise.resolve({ data: [{ id: "s1", title: "Spotify Item" }] });
      if (url.includes("youtube"))
        return Promise.resolve({ data: [{ id: "y1", title: "YouTube Item" }] });
      if (url.includes("deezer"))
        return Promise.resolve({ data: [{ id: "d1", title: "Deezer Item" }] });
      return Promise.resolve({ data: [] });
    });

    renderSearch();
    fireEvent.click(screen.getByTestId("search-all-btn"));

    await waitFor(() => {
      expect(screen.getByText("Spotify Item")).toBeInTheDocument();
      expect(screen.getAllByText("YouTube Item").length).toBeGreaterThan(0);
      expect(screen.getByText("Deezer Item")).toBeInTheDocument();
    });
  });

  it("initializes from URL and performs auto-search", async () => {
    (api.get as unknown as Mock).mockResolvedValue({
      data: [{ id: "u1", title: "URL Param Result" }],
    });

    renderSearch("/search?q=hello&source=spotify&type=track");

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        "/spotify/search",
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
});
