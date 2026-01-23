import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Import from "./Import";

// Mock child component
vi.mock("../components/import/PlaylistImport", () => ({
  default: () => <div data-testid="playlist-import">Playlist Import Component</div>,
}));

describe("Import Page", () => {
  it("renders import page content", () => {
    render(<Import />);
    expect(screen.getByTestId("playlist-import")).toBeInTheDocument();
  });
});
