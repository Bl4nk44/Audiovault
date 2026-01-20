import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useTranslation } from "./useTranslation";

// Mock the store
vi.mock("../store/useStore", () => ({
  useStore: vi.fn((selector) => {
    const mockState = {
      user: null,
    };
    return selector(mockState);
  }),
}));

// Mock translations
vi.mock("../i18n/translations", () => ({
  translations: {
    en: {
      common: {
        save: "Save",
        cancel: "Cancel",
        loading: "Loading...",
      },
      player: {
        play: "Play",
        pause: "Pause",
        next: "Next",
      },
      nested: {
        deep: {
          value: "Deep Nested Value",
        },
      },
    },
    pl: {
      common: {
        save: "Zapisz",
        cancel: "Anuluj",
      },
      player: {
        play: "Odtwórz",
        pause: "Pauza",
      },
    },
  },
}));

import { useStore } from "../store/useStore";

describe("useTranslation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("default language (en)", () => {
    beforeEach(() => {
      vi.mocked(useStore).mockImplementation((selector) => {
        return selector({ user: null } as never);
      });
    });

    it("should return translation for simple path", () => {
      const { result } = renderHook(() => useTranslation());

      expect(result.current.t("common.save")).toBe("Save");
    });

    it("should return translation for nested path", () => {
      const { result } = renderHook(() => useTranslation());

      expect(result.current.t("player.play")).toBe("Play");
    });

    it("should return deeply nested translation", () => {
      const { result } = renderHook(() => useTranslation());

      expect(result.current.t("nested.deep.value")).toBe("Deep Nested Value");
    });

    it("should return path if translation not found", () => {
      const { result } = renderHook(() => useTranslation());

      expect(result.current.t("nonexistent.path")).toBe("nonexistent.path");
    });

    it("should return default language as en", () => {
      const { result } = renderHook(() => useTranslation());

      expect(result.current.language).toBe("en");
    });
  });

  describe("user language preference", () => {
    it("should use user preferred language", () => {
      vi.mocked(useStore).mockImplementation((selector) => {
        return selector({
          user: {
            id: "1",
            email: "test@test.com",
            username: "test",
            preferences: { language: "pl" },
          },
        } as never);
      });

      const { result } = renderHook(() => useTranslation());

      expect(result.current.t("common.save")).toBe("Zapisz");
      expect(result.current.language).toBe("pl");
    });

    it("should fallback to English for missing translations", () => {
      vi.mocked(useStore).mockImplementation((selector) => {
        return selector({
          user: {
            id: "1",
            email: "test@test.com",
            username: "test",
            preferences: { language: "pl" },
          },
        } as never);
      });

      const { result } = renderHook(() => useTranslation());

      // 'loading' doesn't exist in Polish translations
      expect(result.current.t("common.loading")).toBe("Loading...");
    });
  });
});
