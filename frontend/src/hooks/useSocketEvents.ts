import { useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";

/**
 * Hook that connects to the backend Socket.IO server and bridges events
 * to the global event system used by React components.
 */
export function useSocketEvents() {
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // Determine WebSocket URL from environment or fallback to current origin
    const apiUrl = import.meta.env.VITE_API_URL || "";
    const wsUrl = apiUrl.replace(/\/api\/v1\/?$/, "") || globalThis.location.origin;

    console.log("[Socket.IO] Connecting to:", wsUrl);

    const socket = io(wsUrl, {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("[Socket.IO] Connected:", socket.id);
    });

    socket.on("disconnect", (reason) => {
      console.log("[Socket.IO] Disconnected:", reason);
    });

    socket.on("connect_error", (error) => {
      console.error("[Socket.IO] Connection error:", error.message);
    });

    // Bridge download events to global CustomEvents
    socket.on("download:progress", (data) => {
      globalThis.dispatchEvent(new CustomEvent("download:progress", { detail: data }));
    });

    socket.on("download:completed", (data) => {
      globalThis.dispatchEvent(new CustomEvent("download:completed", { detail: data }));
    });

    socket.on("download:error", (data) => {
      globalThis.dispatchEvent(new CustomEvent("download:error", { detail: data }));
    });

    socket.on("download:processing", (data) => {
      globalThis.dispatchEvent(new CustomEvent("download:processing", { detail: data }));
    });

    socket.on("download:paused", (data) => {
      globalThis.dispatchEvent(new CustomEvent("download:paused", { detail: data }));
    });

    socket.on("download:cancelled", (data) => {
      globalThis.dispatchEvent(new CustomEvent("download:cancelled", { detail: data }));
    });

    return () => {
      console.log("[Socket.IO] Cleaning up connection");
      socket.disconnect();
    };
  }, []);

  return socketRef;
}
