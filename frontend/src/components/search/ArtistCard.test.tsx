import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ArtistCard from "./ArtistCard";
import type { Artist } from "../../types";

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({
      children,
      onClick,
      className,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
      className?: string;
    }) => (
      <div onClick={onClick} className={className} data-testid="artist-card">
        {children}
      </div>
    ),
    button: ({
      children,
      onClick,
      disabled,
      className,
      title,
    }: {
      children: React.ReactNode;
      onClick?: (e: React.MouseEvent) => void;
      disabled?: boolean;
      className?: string;
      title?: string;
    }) => (
      <button onClick={onClick} disabled={disabled} className={className} title={title}>
        {children}
      </button>
    ),
  },
}));

// Mock API
vi.mock("../../services/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

// Mock notify
vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import api from "../../services/api";
import { notify } from "../../utils/notify";

describe("ArtistCard", () => {
  const mockArtist: Artist = {
    id: "artist-1",
    name: "Test Artist",
    source: "spotify",
    image_url: "https://example.com/artist.jpg",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderArtistCard = (artist: Artist = mockArtist) => {
    return render(
      <MemoryRouter>
        <ArtistCard artist={artist} />
      </MemoryRouter>
    );
  };

  it("should render artist name", () => {
    renderArtistCard();

    expect(screen.getByText("Test Artist")).toBeTruthy();
  });

  it("should render source", () => {
    renderArtistCard();

    expect(screen.getByText("spotify")).toBeTruthy();
  });

  it("should render artist image when available", () => {
    renderArtistCard();

    const img = screen.getByAltText("Test Artist");
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe("https://example.com/artist.jpg");
  });

  it("should render fallback when no image", () => {
    const artistWithoutImage = { ...mockArtist, image_url: undefined };
    renderArtistCard(artistWithoutImage);

    expect(screen.queryByAltText("Test Artist")).toBeNull();
  });

  it("should navigate to artist page on click", async () => {
    const user = userEvent.setup();
    renderArtistCard();

    await user.click(screen.getByTestId("artist-card"));

    expect(mockNavigate).toHaveBeenCalledWith("/artist/artist-1", {
      state: { source: "spotify" },
    });
  });

  it("should add to watchlist when button is clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    renderArtistCard();

    const addButton = screen.getByTitle("Add to Watchlist");
    await user.click(addButton);

    expect(api.post).toHaveBeenCalledWith(
      "/watchlist/add",
      expect.objectContaining({
        watch_type: "artist",
        source: "spotify",
        source_id: "artist-1",
        source_name: "Test Artist",
        auto_download: true,
      })
    );
    expect(notify.success).toHaveBeenCalledWith("Artist added to watchlist");
  });

  it("should show error when adding to watchlist fails", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockRejectedValue(new Error("Failed"));
    renderArtistCard();

    const addButton = screen.getByTitle("Add to Watchlist");
    await user.click(addButton);

    expect(notify.error).toHaveBeenCalledWith("Failed to add to watchlist");
  });

  it('should change button to "Added" state after successful add', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    renderArtistCard();

    const addButton = screen.getByTitle("Add to Watchlist");
    await user.click(addButton);

    expect(screen.getByTitle("Added")).toBeTruthy();
  });

  it("should disable button after adding", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    renderArtistCard();

    const addButton = screen.getByTitle("Add to Watchlist");
    await user.click(addButton);

    const disabledButton = screen.getByTitle("Added");
    expect(disabledButton).toBeDisabled();
  });
});
