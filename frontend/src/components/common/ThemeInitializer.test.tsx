import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStore } from "../../store/useStore";
import { ThemeInitializer } from "./ThemeInitializer";

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

describe("ThemeInitializer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.documentElement.className = "";
  });

  const mockStore = (user: any) => {
    vi.mocked(useStore).mockImplementation((selector: any) => selector({ user }));
  };

  it("applies dark theme by default", () => {
    mockStore(null);
    render(<ThemeInitializer />);
    expect(document.documentElement.className).toBe("dark");
  });

  it("applies theme from user preferences", () => {
    mockStore({
      preferences: { theme: "light" },
    });
    render(<ThemeInitializer />);
    expect(document.documentElement.className).toBe("light");
  });

  it("applies theme from legacy storage if user state is missing", () => {
    mockStore(null);

    const legacySession = {
      "session-1": {
        token: "mock-token",
        user: { preferences: { theme: "light" } },
      },
    };

    const storage = globalThis.localStorage as any;
    storage.getItem.mockImplementation((key: string) => {
      if (key === "sessions") return JSON.stringify(legacySession);
      if (key === "access_token") return "mock-token";
      return null;
    });

    render(<ThemeInitializer />);
    expect(document.documentElement.className).toBe("light");
  });

  it("handles corrupt legacy storage", () => {
    mockStore(null);
    const storage = globalThis.localStorage as any;
    storage.getItem.mockImplementation((key: string) => {
      if (key === "sessions") return "invalid-json";
      if (key === "access_token") return "mock-token";
      return null;
    });

    render(<ThemeInitializer />);
    expect(document.documentElement.className).toBe("dark");
  });
});
