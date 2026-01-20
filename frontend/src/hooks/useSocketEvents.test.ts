import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useSocketEvents } from "./useSocketEvents";

// Mock socket.io-client
const mockSocket = {
  on: vi.fn(),
  disconnect: vi.fn(),
  id: "mock-socket-id",
};

vi.mock("socket.io-client", () => ({
  io: vi.fn(() => mockSocket),
}));

import { io } from "socket.io-client";

describe("useSocketEvents", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock socket handlers
    mockSocket.on.mockClear();
    mockSocket.disconnect.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should connect to socket server", () => {
    renderHook(() => useSocketEvents());

    expect(io).toHaveBeenCalled();
    expect(io).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        path: "/socket.io",
        transports: ["websocket", "polling"],
      }),
    );
  });

  it("should register connect event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith("connect", expect.any(Function));
  });

  it("should register disconnect event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "disconnect",
      expect.any(Function),
    );
  });

  it("should register connect_error event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "connect_error",
      expect.any(Function),
    );
  });

  it("should register download:progress event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "download:progress",
      expect.any(Function),
    );
  });

  it("should register download:completed event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "download:completed",
      expect.any(Function),
    );
  });

  it("should register download:error event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "download:error",
      expect.any(Function),
    );
  });

  it("should register download:processing event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "download:processing",
      expect.any(Function),
    );
  });

  it("should register download:paused event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "download:paused",
      expect.any(Function),
    );
  });

  it("should register download:cancelled event handler", () => {
    renderHook(() => useSocketEvents());

    expect(mockSocket.on).toHaveBeenCalledWith(
      "download:cancelled",
      expect.any(Function),
    );
  });

  it("should disconnect socket on unmount", () => {
    const { unmount } = renderHook(() => useSocketEvents());

    unmount();

    expect(mockSocket.disconnect).toHaveBeenCalled();
  });

  it("should return socket ref", () => {
    const { result } = renderHook(() => useSocketEvents());

    expect(result.current.current).toBe(mockSocket);
  });

  it("should dispatch CustomEvent on download:progress", () => {
    const dispatchSpy = vi.spyOn(globalThis, "dispatchEvent");

    renderHook(() => useSocketEvents());

    // Find and call the download:progress handler
    const progressHandler = mockSocket.on.mock.calls.find(
      (call) => call[0] === "download:progress",
    )?.[1];

    if (progressHandler) {
      progressHandler({ download_id: "dl-1", progress: 50 });
    }

    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "download:progress",
        detail: { download_id: "dl-1", progress: 50 },
      }),
    );
  });
});
