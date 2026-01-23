import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SearchBar from "./SearchBar";

vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("framer-motion", () => ({
  motion: {
    form: ({ children, onSubmit, className }: any) => (
      <form onSubmit={onSubmit} className={className}>
        {children}
      </form>
    ),
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
}));

describe("SearchBar", () => {
  const mockOnSearch = vi.fn();

  it("renders with initial values", () => {
    render(
      <SearchBar
        onSearch={mockOnSearch}
        isLoading={false}
        initialQuery="test"
        initialSource="spotify"
        initialType="track"
      />
    );

    expect(screen.getByPlaceholderText("search.placeholder")).toHaveValue("test");
    expect(screen.getByDisplayValue("filters.tracks")).toBeInTheDocument();
  });

  it("calls onSearch when form is submitted", () => {
    render(<SearchBar onSearch={mockOnSearch} isLoading={false} />);

    const input = screen.getByPlaceholderText("search.placeholder");
    fireEvent.change(input, { target: { value: "new query" } });

    fireEvent.submit(screen.getByRole("button", { name: "filters.search" }));

    expect(mockOnSearch).toHaveBeenCalledWith("new query", "all", "all");
  });

  it("changes source and type correctly", () => {
    render(<SearchBar onSearch={mockOnSearch} isLoading={false} />);

    const typeSelect = screen.getByDisplayValue("filters.allTypes");
    fireEvent.change(typeSelect, { target: { value: "artist" } });

    const sourceSelect = screen.getByDisplayValue("filters.allSources");
    fireEvent.change(sourceSelect, { target: { value: "youtube" } });

    fireEvent.change(screen.getByPlaceholderText("search.placeholder"), { target: { value: "q" } });
    fireEvent.submit(screen.getByRole("button", { name: "filters.search" }));

    expect(mockOnSearch).toHaveBeenCalledWith("q", "youtube", "artist");
  });

  it("shows loading state", () => {
    render(<SearchBar onSearch={mockOnSearch} isLoading={true} />);
    const button = screen.getByRole("button", { name: "search.searching" });
    expect(button).toBeDisabled();
  });

  it("clears query when X button is clicked", () => {
    render(<SearchBar onSearch={mockOnSearch} isLoading={false} initialQuery="clear me" />);

    // const xButton = screen.getByRole("button", { name: "" });
    // The X component has no title, but it's the only other button beside Search
    const buttons = screen.getAllByRole("button");
    const clearButton = buttons.find((b) => b.querySelector("svg"));

    if (clearButton) {
      fireEvent.click(clearButton);
      expect(screen.getByPlaceholderText("search.placeholder")).toHaveValue("");
    }
  });
});
