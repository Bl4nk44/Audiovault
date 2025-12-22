import React from "react";
import { useStore } from "../../store/useStore";

export function SessionManager() {
  const isAuthenticated = useStore((state) => state.isAuthenticated);
  const syncUser = useStore((state) => state.syncUser);

  React.useEffect(() => {
    if (isAuthenticated) {
      // Dynamic import to avoid circular dependency
      import("../../services/api").then(({ default: api }) => {
        api
          .get("/users/me")
          .then((res) => {
            if (res.data) {
              syncUser(res.data);
            }
          })
          .catch((err) => {
            console.error("Failed to restore session user data:", err);
            // If 401, the interceptor will handle logout.
          });
      });
    }
  }, [isAuthenticated, syncUser]);

  // WebSocket Intialization
  React.useEffect(() => {
    import("../../services/websocket");
  }, []);

  return null;
}
