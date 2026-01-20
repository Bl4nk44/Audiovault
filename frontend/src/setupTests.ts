// setupTests.ts
// Globalna konfiguracja testów dla Vitest + React Testing Library

import "@testing-library/jest-dom/vitest";
import { vi, beforeEach, afterEach } from "vitest";

declare global {
  var localStorage: Storage;
  var ResizeObserver: typeof ResizeObserver;
  var IntersectionObserver: typeof IntersectionObserver;
}

// Mock localStorage
const localStorageMock: Storage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};
Object.defineProperty(globalThis, "localStorage", { value: localStorageMock });

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock ResizeObserver
vi.stubGlobal(
  "ResizeObserver",
  vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }))
);

// Mock IntersectionObserver
vi.stubGlobal(
  "IntersectionObserver",
  vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }))
);

// Mock window.location.reload
Object.defineProperty(window, "location", {
  writable: true,
  value: {
    ...window.location,
    reload: vi.fn(),
  },
});

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks();
  (localStorageMock.getItem as any).mockReturnValue(null);
});

// Cleanup after each test
afterEach(() => {
  vi.restoreAllMocks();
});
