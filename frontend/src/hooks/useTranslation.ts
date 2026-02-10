import { translations } from "../i18n/translations";
import { useStore } from "../store/useStore";

import { useCallback } from "react";

type TranslationMap = { [key: string]: string | TranslationMap };

function getNestedValue(obj: TranslationMap | string, keys: string[]): string | undefined {
  let current: TranslationMap | string = obj;

  for (const key of keys) {
    if (
      current === undefined ||
      typeof current === "string" ||
      typeof current !== "object" ||
      current === null ||
      !(key in current)
    ) {
      return undefined;
    }
    current = current[key];
  }

  return typeof current === "string" ? current : undefined;
}

export function useTranslation() {
  const user = useStore((state) => state.user);
  const language = (user?.preferences?.language as keyof typeof translations) || "en";

  const t = useCallback(
    (path: string, defaultValue?: string): string => {
      const keys = path.split(".");

      // Try current language
      const currentTranslation = translations[language];
      if (currentTranslation) {
        const found = getNestedValue(currentTranslation, keys);
        if (found) return found;
      }

      // Fallback to English
      if (language !== "en") {
        const fallbackTranslation = translations["en"];
        const found = getNestedValue(fallbackTranslation, keys);
        if (found) return found;
      }

      return defaultValue || path;
    },
    [language]
  );

  return { t, language };
}
