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
    // nosemgrep: javascript.lang.security.audit.prototype-pollution.prototype-pollution-loop.prototype-pollution-loop
    current = current[key];
  }

  return typeof current === "string" ? current : undefined;
}

export function useTranslation() {
  const user = useStore((state) => state.user);
  const language = (user?.preferences?.language as keyof typeof translations) || "en";

  const t = useCallback(
    (path: string, defaultValue?: string, vars?: Record<string, string | number>): string => {
      const keys = path.split(".");

      let result: string | undefined;

      // Try current language
      const currentTranslation = translations[language];
      if (currentTranslation) {
        result = getNestedValue(currentTranslation, keys);
      }

      // Fallback to English
      if (result === undefined && language !== "en") {
        result = getNestedValue(translations["en"], keys);
      }

      if (result === undefined) result = defaultValue ?? path;

      // Interpolate {{var}} placeholders
      if (vars) {
        for (const [key, value] of Object.entries(vars)) {
          result = result.split(`{{${key}}}`).join(String(value));
        }
      }

      return result;
    },
    [language]
  );

  return { t, language };
}
