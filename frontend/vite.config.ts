/// <reference types="vitest" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vitest/config";

// Read version from VERSION file
// In Docker: VERSION is copied to same directory
// Locally: VERSION is in parent directory
let version = "0.0.0";
const versionPaths = [
  path.resolve(__dirname, "VERSION"), // Docker build (same dir)
  path.resolve(__dirname, "../VERSION"), // Local development (parent)
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
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-framer": ["framer-motion"],
          "vendor-icons": ["lucide-react"],
          "vendor-utils": ["clsx", "tailwind-merge", "zustand", "axios"],
          "vendor-query": ["@tanstack/react-query"],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
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
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      reportsDirectory: "./coverage",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "node_modules/",
        "src/setupTests.ts",
        "src/**/*.test.{ts,tsx}",
        "src/**/*.spec.{ts,tsx}",
        "src/**/*.d.ts",
        "src/main.tsx",
        "src/vite-env.d.ts",
      ],
      thresholds: {
        // TODO: Gradually increase thresholds as more tests are added
        // Current baseline: 20%, Target: 80% (Phase 2)
        lines: 20,
        branches: 15,
        functions: 25,
        statements: 20,
      },
    },
  },
});
