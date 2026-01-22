// setupTests.ts
import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi } from "vitest";

console.log("--> Loading setupTests.ts with FakeAudioContext");

// 1. Create Mock Objects
const localStorageMock = {
  getItem: vi.fn(() => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(() => null),
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

// 2. Define AudioContext Mock Class
class FakeAudioContext {
  state = "suspended";
  destination = {};

  constructor() {
    console.log("--> FakeAudioContext instantiated");
  }

  createAnalyser() {
    return {
      connect: vi.fn(),
      disconnect: vi.fn(),
      frequencyBinCount: 1024,
      getByteFrequencyData: vi.fn(),
      smoothingTimeConstant: 0.8,
      fftSize: 2048,
    };
  }

  createMediaElementSource() {
    return {
      connect: vi.fn(),
    };
  }

  close() {
    return Promise.resolve();
  }
  resume() {
    return Promise.resolve();
  }
  suspend() {
    return Promise.resolve();
  }
}

// 3. Register Global Mocks
vi.stubGlobal("localStorage", localStorageMock);
vi.stubGlobal("ResizeObserver", resizeObserverMock);
vi.stubGlobal("IntersectionObserver", intersectionObserverMock);

// Stub AudioContext globally using vi.stubGlobal (safest for Vitest)
vi.stubGlobal("AudioContext", FakeAudioContext);
vi.stubGlobal("webkitAudioContext", FakeAudioContext);

// 4. Fallback: manual assignment to window/globalThis just in case
if (typeof window !== "undefined") {
  window.AudioContext = FakeAudioContext as any;
  window.webkitAudioContext = FakeAudioContext as any;
}
globalThis.AudioContext = FakeAudioContext as any;
globalThis.webkitAudioContext = FakeAudioContext as any;

// 5. Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
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

// 6. Mock location
Object.defineProperty(window, "location", {
  writable: true,
  value: {
    ...window.location,
    reload: vi.fn(),
  },
});

// Hooks
beforeEach(() => {
  vi.clearAllMocks();
  (localStorageMock.getItem as any).mockReturnValue(null);
});

afterEach(() => {
  vi.restoreAllMocks();
});
