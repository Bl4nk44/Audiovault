import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Settings from "./Settings";

// Mock dependencies
vi.mock("../hooks/useTranslation", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../components/settings/SettingsPanel", () => ({
  default: () => <div data-testid="settings-panel">Settings Panel Content</div>,
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className }: any) => <div className={className}>{children}</div>,
  },
}));

describe("Settings Page", () => {
  it("renders settings header and panel", () => {
    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    );

    expect(screen.getByText("common.settings")).toBeInTheDocument();
    expect(screen.getByText("settings.subtitle")).toBeInTheDocument();
    expect(screen.getByTestId("settings-panel")).toBeInTheDocument();
  });
});
