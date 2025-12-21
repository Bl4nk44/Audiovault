import { io, Socket } from "socket.io-client";
import { API_URL } from "./api";
import type {
  DownloadProgressDetail,
  DownloadCompletedDetail,
  DownloadErrorDetail,
} from "../types/events";

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor() {
    this.connect();
  }

  public connect() {
    if (this.socket?.connected) return;

    // Remove /api/v1 from API_URL to get base URL
    const baseUrl = API_URL.replace("/api/v1", "");

    this.socket = io(baseUrl, {
      path: "/socket.io",
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      autoConnect: true,
    });

    this.setupListeners();
  }

  private setupListeners() {
    if (!this.socket) return;

    this.socket.on("connect", () => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0;
    });

    this.socket.on("disconnect", () => {
      console.log("WebSocket disconnected");
    });

    this.socket.on("connect_error", (error) => {
      console.error("WebSocket connection error:", error);
      this.reconnectAttempts++;
    });

    // Handle download progress
    this.socket.on("download_progress", (data: DownloadProgressDetail) => {
      const event = new CustomEvent("download:progress", {
        detail: data,
      });
      globalThis.dispatchEvent(event);
    });

    // Handle download completion
    this.socket.on("download_completed", (data: DownloadCompletedDetail) => {
      const event = new CustomEvent("download:completed", {
        detail: data,
      });
      globalThis.dispatchEvent(event);
    });

    // Handle download error
    this.socket.on("download_error", (data: DownloadErrorDetail) => {
      const event = new CustomEvent("download:error", {
        detail: data,
      });
      globalThis.dispatchEvent(event);
    });
  }

  public disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  public getSocket(): Socket | null {
    return this.socket;
  }
}

export const webSocketService = new WebSocketService();
export default webSocketService;
