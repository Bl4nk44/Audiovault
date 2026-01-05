import { useStore } from "../store/useStore";
import { translations } from "../i18n/translations";

import { useCallback } from "react";

export function useTranslation() {
  const user = useStore((state) => state.user);
  const language =
    (user?.preferences?.language as keyof typeof translations) || "en";

  // Simple recursive lookup
  type TranslationMap = { [key: string]: string | TranslationMap };

  const t = useCallback(
    (path: string): string => {
      const keys = path.split(".");
      let current: TranslationMap | string =
        translations[language] || translations["en"];

      for (const key of keys) {
        if (
          current === undefined ||
          typeof current === "string" ||
          (current as TranslationMap)[key] === undefined
        ) {
          // Fallback to English if translation missing
          if (language !== "en") {
            let fallback: TranslationMap | string = translations["en"];
            for (const fKey of keys) {
              if (
                fallback === undefined ||
                typeof fallback === "string" ||
                (fallback as TranslationMap)[fKey] === undefined
              )
                return path;
              fallback = (fallback as TranslationMap)[fKey];
            }
            return fallback as string;
          }
          return path;
        }
        current = (current as TranslationMap)[key];
      }
      return current as string;
    },
    [language]
  );

  return { t, language };
}
