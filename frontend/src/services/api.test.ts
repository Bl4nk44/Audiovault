import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import axios from "axios";

// Mock axios before importing api
vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      defaults: {
        headers: {
          common: {},
        },
      },
    })),
    post: vi.fn(),
  },
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};
Object.defineProperty(global, "localStorage", { value: localStorageMock });

// Mock import.meta.env
vi.stubGlobal("import", {
  meta: {
    env: {
      VITE_API_URL: "/api/v1",
    },
  },
});

describe("API Service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("API creation", () => {
    it("should create axios instance with correct base URL", async () => {
      // Dynamic import to get fresh instance
      const { API_URL } = await import("./api");

      expect(API_URL).toBe("/api/v1");
    });
  });

  describe("injectStore", () => {
    it("should inject store successfully", async () => {
      const { injectStore } = await import("./api");

      const mockStore = {
        getState: vi.fn(() => ({
          logout: vi.fn(),
          setTokens: vi.fn(),
        })),
      };

      expect(() => injectStore(mockStore)).not.toThrow();
    });
  });
});
