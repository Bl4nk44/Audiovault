import React from "react";
import { useStore } from "../../store/useStore";

export function ThemeInitializer() {
  const user = useStore((state) => state.user);

  React.useLayoutEffect(() => {
    let theme = user?.preferences?.theme;

    // Fallback to localStorage if user state not ready
    if (!theme) {
      try {
        const stored = localStorage.getItem("sessions");
        if (stored) {
          const sessions = JSON.parse(stored);
          const currentToken = localStorage.getItem("access_token");
          if (currentToken) {
            // Define minimal interface for legacy session parsing
            interface LegacySession {
              token?: string;
              user?: { preferences?: { theme?: string } };
            }
            const session = Object.values(sessions).find(
              (s) => (s as LegacySession).token === currentToken
            ) as LegacySession | undefined;
            if (session?.user?.preferences?.theme) {
              const legacyTheme = session.user.preferences.theme;
              if (legacyTheme === "light" || legacyTheme === "dark") {
                theme = legacyTheme;
              }
            }
          }
        }
      } catch {
        // Ignore parsing errors
      }
    }

    // specific fallback: if still no theme, check if 'classic' was previously set (legacy) and default to 'dark'
    // otherwise use 'dark' as safe default
    if (!theme) theme = "dark";

    document.documentElement.className = theme;
  }, [user?.preferences?.theme]);

  // Handle immediate application on mount to ensure sync
  React.useLayoutEffect(() => {
    const savedClass = document.documentElement.className;
    if (user?.preferences?.theme && savedClass !== user.preferences.theme) {
      document.documentElement.className = user.preferences.theme;
    }
  }, [user]);

  return null;
}
