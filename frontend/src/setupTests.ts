// setupTests.ts
// Globalna konfiguracja testów dla Vitest + React Testing Library

import "@testing-library/jest-dom/vitest";
import { vi, beforeEach, afterEach } from "vitest";

// Create proper mock objects with correct types
const localStorageMock: Storage = {
  getItem: vi.fn(() => null) as any,
  setItem: vi.fn() as any,
  removeItem: vi.fn() as any,
  clear: vi.fn() as any,
  length: 0,
  key: vi.fn(() => null) as any,
};

const resizeObserverMock = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

const intersectionObserverMock = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Set up global mocks using vi.stubGlobal
vi.stubGlobal('localStorage', localStorageMock);
vi.stubGlobal('ResizeObserver', resizeObserverMock);
vi.stubGlobal('IntersectionObserver', intersectionObserverMock);

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
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

// Mock window.location.reload
Object.defineProperty(window, 'location', {
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
