/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import fs from "fs";
import path from "path";

// Read version from VERSION file
// In Docker: VERSION is copied to same directory
// Locally: VERSION is in parent directory
let version = "0.0.0";
const versionPaths = [
  path.resolve(__dirname, "VERSION"),      // Docker build (same dir)
  path.resolve(__dirname, "../VERSION"),   // Local development (parent)
];

for (const versionPath of versionPaths) {
  try {
    version = fs.readFileSync(versionPath, "utf-8").trim();
    break; // Found it, stop looking
  } catch {
    // Try next path
  }
}

if (version === "0.0.0") {
  console.warn("Could not read VERSION file, using fallback 0.0.0");
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
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts', 
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      exclude: ['node_modules/', 'src/setupTests.ts'],
    },
  },
});
