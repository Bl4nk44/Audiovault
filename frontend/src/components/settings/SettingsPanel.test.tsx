import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { useTranslation } from "../../hooks/useTranslation";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
import { notify } from "../../utils/notify";
import SettingsPanel from "./SettingsPanel";

// Mock dependencies
vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: vi.fn(),
}));

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("./AccountSettings", () => ({
  default: () => <div data-testid="account-settings">Account Settings</div>,
}));

// Mock Lucide icons
vi.mock("lucide-react", () => ({
  Download: () => <div>Icon-Download</div>,
  FileText: () => <div>Icon-FileText</div>,
  FolderOpen: () => <div>Icon-FolderOpen</div>,
  Globe: () => <div>Icon-Globe</div>,
  Palette: () => <div>Icon-Palette</div>,
  Save: () => <div>Icon-Save</div>,
  User: () => <div>Icon-User</div>,
}));

describe("SettingsPanel", () => {
  const mockUpdateUserPreferences = vi.fn();
  const mockChangeLanguage = vi.fn();
  const mockSetTheme = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock Store
    (useStore as unknown as Mock).mockImplementation((selector) => {
      const state = {
        theme: "dark",
        setTheme: mockSetTheme,
        updateUserPreferences: mockUpdateUserPreferences,
      };
      return selector ? selector(state) : state;
    });

    // Mock Translation
    (useTranslation as unknown as Mock).mockReturnValue({
      t: (key: string) => key,
      i18n: {
        changeLanguage: mockChangeLanguage,
        language: "en",
      },
    });

    // Mock API
    (api.get as unknown as Mock).mockResolvedValue({
      data: {
        language: "en",
        theme: "dark",
        downloadPath: "/downloads",
        filenameSchema: "{artist} - {title}",
        maxParallelDownloads: 3,
        audioQuality: "high",
      },
    });

    (api.post as unknown as Mock).mockResolvedValue({ data: {} });
  });

  it("renders settings tabs", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    // Check elements exist (handling duplicates)
    expect(screen.getAllByText("settings.general").length).toBeGreaterThan(0);
    expect(screen.getByText("settings.appearance")).toBeInTheDocument();
    expect(screen.getByText("settings.files")).toBeInTheDocument();
    expect(screen.getByText("settings.account")).toBeInTheDocument();
  });

  it("switches tabs correctly", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    // Switch to Account
    fireEvent.click(screen.getByText("settings.account"));
    expect(screen.getByTestId("account-settings")).toBeInTheDocument();

    // Switch to Appearance
    fireEvent.click(screen.getByText("settings.appearance"));
    expect(screen.getByText("settings.themes.ocean")).toBeInTheDocument();
  });

  it("handles language change", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    // Assuming we are on General tab (default)
    // Find the language select - wait for it to appear
    const selects = await screen.findAllByRole("combobox");
    // First one should be language based on order in code
    const langSelect = selects[0];

    fireEvent.change(langSelect, { target: { value: "pl" } });

    // The component manages local state for settings, doesn't call i18n.changeLanguage until save?
    // Or maybe it does?
    // In SettingsPanel.tsx: onChange={(e) => setSettings({ ...settings, language: e.target.value })}
    // It only updates state. It does NOT call changeLanguage immediately in the code I saw.
    // So checking mockChangeLanguage might be wrong if it's not called on change.
    // Let's check if value updated.

    expect(langSelect).toHaveValue("pl");
  });

  it("saves settings to API", async () => {
    render(<SettingsPanel />);

    // Wait for the save button to appear (loading finished)
    const saveBtn = await screen.findByText("common.save");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/settings/",
        expect.objectContaining({
          language: "en", // default mocked
          theme: "dark",
        })
      );
      expect(notify.success).toHaveBeenCalledWith("common.saved");
    });
  });

  it("updates input fields", async () => {
    render(<SettingsPanel />);
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    // Go to files tab
    fireEvent.click(screen.getByText("settings.files"));

    const input = screen.getByDisplayValue("/downloads");
    fireEvent.change(input, { target: { value: "/new/path" } });

    expect(input).toHaveValue("/new/path");
  });
});
