import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import fs from "fs";
import path from "path";

// Read version from root directory or fallback
let version = "0.0.0";
try {
  version = fs
    .readFileSync(path.resolve(__dirname, "../VERSION"), "utf-8")
    .trim();
} catch {
  console.warn(
    "Could not read VERSION file (likely in Docker build), using fallback."
  );
}

// https://vite.dev/config/
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
      },
      "/rest": {
        target: process.env.BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on("proxyReq", (_, req) => {
            console.log("VITE PROXY: [Subsonic] sending to:", req.url);
          });
        },
      },
      "/stream": {
        target: process.env.BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
      },
      "/static": {
        target: process.env.BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
      },
      "/socket.io": {
        target: process.env.BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
