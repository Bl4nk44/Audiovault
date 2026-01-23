import { fireEvent, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Watchlist from "./Watchlist";

// Mock child components
vi.mock("../components/watchlist/WatchlistManager", () => ({
  default: () => <div data-testid="watchlist-manager">Watchlist Manager Content</div>,
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("Watchlist Page", () => {
  it("renders watchlist header and manager", () => {
    render(
      <BrowserRouter>
        <Watchlist />
      </BrowserRouter>
    );

    expect(screen.getByText("Watchlist")).toBeInTheDocument();
    expect(screen.getByText(/Track new releases/i)).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-manager")).toBeInTheDocument();
  });

  it("navigates to search on add new click", () => {
    render(
      <BrowserRouter>
        <Watchlist />
      </BrowserRouter>
    );

    const addBtn = screen.getByText("+ Add New");
    fireEvent.click(addBtn);

    expect(mockNavigate).toHaveBeenCalledWith("/search");
  });
});
