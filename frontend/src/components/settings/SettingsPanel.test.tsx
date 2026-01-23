import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../../services/api";
import SettingsPanel from "./SettingsPanel";

// Mock dependencies
vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));
vi.mock("../../store/useStore", () => ({
  useStore: (selector: any) => {
    const state = { updateUserPreferences: vi.fn() };
    return selector ? selector(state) : state;
  },
}));
vi.mock("../../utils/notify", () => ({
  notify: { success: vi.fn(), error: vi.fn() },
}));
vi.mock("./AccountSettings", () => ({
  default: () => <div data-testid="account-settings">Account Settings</div>,
}));
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className }: any) => <div className={className}>{children}</div>,
    button: ({ children, onClick, className }: any) => (
      <button onClick={onClick} className={className}>
        {children}
      </button>
    ),
  },
}));

// Mock lucide-react content
vi.mock("lucide-react", () => ({
  Download: () => <div data-testid="icon-download" />,
  FileText: () => <div data-testid="icon-file-text" />,
  FolderOpen: () => <div data-testid="icon-folder-open" />,
  Globe: () => <div data-testid="icon-globe" />,
  Palette: () => <div data-testid="icon-palette" />,
  Save: () => <div data-testid="icon-save" />,
  User: ({ size }: any) => <div data-testid="icon-user" data-size={size} />,
}));

describe("SettingsPanel Component", () => {
  const mockSettings = {
    spotifyClientId: "id",
    spotifyClientSecret: "secret",
    theme: "dark",
    language: "en",
    downloadPath: "/downloads",
    filenameSchema: "{artist} - {title}",
    maxParallelDownloads: 3,
    audioQuality: "high",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockResolvedValue({ data: mockSettings });
    (api.post as any).mockResolvedValue({});
  });

  it("fetches and renders initial settings", async () => {
    (api.get as any).mockResolvedValue({
      data: { ...mockSettings, language: "pl" },
    });
    render(<SettingsPanel />);

    await waitFor(() => {
      expect(screen.queryByText("common.loading")).not.toBeInTheDocument();
    });

    // Check for general tab heading to avoid ambiguity with tab button
    expect(screen.getByRole("heading", { name: "settings.general" })).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledWith("/settings/");
  });

  it("handles tab switching", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(screen.queryByText("common.loading")).not.toBeInTheDocument());

    const accountTab = screen.getByText("settings.account");
    fireEvent.click(accountTab);
    expect(screen.getByTestId("account-settings")).toBeInTheDocument();

    const filesTab = screen.getByText("settings.files");
    fireEvent.click(filesTab);
    // There might be ambiguity here too if sidebar has "settings.files"
    // But content header also has it.
    // Let's use getByRole heading again or check for input unique to files tab
    expect(screen.getByRole("heading", { name: "settings.files" })).toBeInTheDocument();
    expect(screen.getByText("settings.downloadPath")).toBeInTheDocument();
  });

  it("handles setting updates", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(screen.queryByText("common.loading")).not.toBeInTheDocument());

    const filesTab = screen.getByText("settings.files");
    fireEvent.click(filesTab);

    const pathInput = screen.getByDisplayValue("/downloads");
    fireEvent.change(pathInput, { target: { value: "/new/path" } });
    expect(pathInput).toHaveValue("/new/path");
  });

  it("saves settings", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(screen.queryByText("common.loading")).not.toBeInTheDocument());

    const saveBtn = screen.getByText("common.save");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/settings/",
        expect.objectContaining({ theme: "dark" })
      );
    });
  });

  it("handles theme switching", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(screen.queryByText("common.loading")).not.toBeInTheDocument());

    const appearanceTab = screen.getByText("settings.appearance");
    fireEvent.click(appearanceTab);

    // This selector finds the button containing the text
    const oceanThemeText = screen.getByText("settings.themes.ocean");
    const oceanThemeBtn = oceanThemeText.closest("button")!;
    fireEvent.click(oceanThemeBtn);

    expect(document.documentElement.className).toBe("ocean");
  });
});
