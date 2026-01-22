import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../services/api";
import { notify } from "../utils/notify";
import Library from "./Library";

// Mock dependencies
vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock("../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock Store
vi.mock("../store/useStore", () => ({
  useStore: () => ({
    currentTrack: null,
    isPlaying: false,
    playTrack: vi.fn(),
    togglePlay: vi.fn(),
  }),
}));

// Mock i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue: string) => defaultValue || key,
  }),
}));

// Mock framer-motion
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: any) => <>{children}</>,
  motion: {
    div: (props: any) => <div {...props}>{props.children}</div>,
    button: (props: any) => <button {...props}>{props.children}</button>,
    h3: (props: any) => <h3 {...props}>{props.children}</h3>,
    tr: (props: any) => <tr {...props}>{props.children}</tr>,
  },
}));

describe("Library", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mocks
    vi.mocked(api.get).mockImplementation((url) => {
      if (url === "/downloads/library/folders") {
        return Promise.resolve({ data: { spotify: ["My Playlist"] } });
      }
      return Promise.resolve({ data: { items: [], total: 0 } });
    });
  });

  it("should open create playlist modal and call api on submit", async () => {
    render(<Library />);

    // Wait for initial load
    await waitFor(() => expect(screen.getByText("My Library")).toBeTruthy());

    // Click "New Playlist" button
    const newPlaylistBtn = screen.getByText("New Playlist");
    fireEvent.click(newPlaylistBtn);

    // Check if modal opened
    const modalTitle = screen.getByText("Create New Playlist");
    expect(modalTitle).toBeTruthy();

    const input = screen.getByPlaceholderText("My Playlist");
    fireEvent.change(input, { target: { value: "Cool Vibes" } });

    const createBtn = screen.getByText("Create");
    vi.mocked(api.post).mockResolvedValue({ data: {} });

    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/playlists/", {
        name: "Cool Vibes",
        public: false,
      });
      expect(notify.success).toHaveBeenCalledWith("Playlist created");
    });
  });
});
