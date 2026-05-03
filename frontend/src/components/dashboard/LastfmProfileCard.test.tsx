import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LastfmProfileCard from "./LastfmProfileCard";
import { getLastfmProfile } from "../../services/lastfm";
import type { LastfmProfile } from "../../types/lastfm";

// Mock the service
vi.mock("../../services/lastfm", () => ({
  getLastfmProfile: vi.fn(),
}));

describe("LastfmProfileCard", () => {
  const mockProfile: LastfmProfile = {
    user: {
      name: "testuser",
      realname: "Test User",
      url: "http://last.fm/user/testuser",
      country: "Poland",
      age: 25,
      playcount: 1234567,
      artist_count: 500,
      track_count: 1500,
      album_count: 300,
      image_url: "http://example.com/avatar.jpg",
      registered: 1609459200, // 2021-01-01
      subscriber: false,
    },
    friends: [
      {
        name: "friend1",
        realname: "Friend One",
        url: "http://last.fm/user/friend1",
        country: "UK",
        image_url: "http://example.com/friend1.jpg",
      },
      {
        name: "friend2",
        realname: "",
        url: "http://last.fm/user/friend2",
        country: "USA",
        image_url: null,
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    vi.mocked(getLastfmProfile).mockReturnValue(new Promise(() => {}));
    const { container } = render(<LastfmProfileCard username="testuser" />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders profile data correctly", async () => {
    vi.mocked(getLastfmProfile).mockResolvedValue(mockProfile);
    render(<LastfmProfileCard username="testuser" />);

    await waitFor(() => {
      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    expect(screen.getByText("@testuser")).toBeInTheDocument();
    expect(screen.getByText("Poland")).toBeInTheDocument();

    // Check formatted numbers
    expect(screen.getByText("1.2M")).toBeInTheDocument(); // 1234567 -> 1.2M
    expect(screen.getByText("500")).toBeInTheDocument();
    expect(screen.getByText("1.5K")).toBeInTheDocument(); // 1500 -> 1.5K
    expect(screen.getByText("300")).toBeInTheDocument();

    // Check friends
    expect(screen.getByText("Friends (2)")).toBeInTheDocument();
    expect(screen.getByText("friend1")).toBeInTheDocument();
    expect(screen.getByText("friend2")).toBeInTheDocument();
  });

  it("renders nothing on error", async () => {
    vi.mocked(getLastfmProfile).mockRejectedValue(new Error("API Error"));
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<LastfmProfileCard username="testuser" />);

    await waitFor(() => {
      expect(screen.queryByText("Test User")).not.toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });

  it("renders nothing if no username provided", () => {
    render(<LastfmProfileCard username="" />);
    expect(screen.queryByText("Test User")).not.toBeInTheDocument();
  });

  it("renders default avatar when image_url is missing", async () => {
    const profileNoImg = {
      ...mockProfile,
      user: { ...mockProfile.user, image_url: null }
    };
    vi.mocked(getLastfmProfile).mockResolvedValue(profileNoImg);

    render(<LastfmProfileCard username="testuser" />);

    await waitFor(() => {
      expect(screen.getByText("@testuser")).toBeInTheDocument();
    });

    // Should not find the img with alt testuser
    expect(screen.queryByAltText("testuser")).not.toBeInTheDocument();
  });
});
