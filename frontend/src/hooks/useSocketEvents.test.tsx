/* eslint-disable */
import { renderHook } from "@testing-library/react";
import { io } from "socket.io-client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSocketEvents } from "./useSocketEvents";

vi.mock("socket.io-client", () => ({
  io: vi.fn().mockReturnValue({
    on: vi.fn(),
    disconnect: vi.fn(),
  }),
}));

describe("useSocketEvents", () => {
  let mockSocket: any;
  const handlers: Record<string, Function> = {};

  beforeEach(() => {
    vi.clearAllMocks();
    mockSocket = {
      on: vi.fn((event, handler) => {
        handlers[event] = handler;
      }),
      disconnect: vi.fn(),
    };
    (io as any).mockReturnValue(mockSocket);
  });

  it("initializes socket connection", () => {
    renderHook(() => useSocketEvents());
    expect(io).toHaveBeenCalled();
    expect(mockSocket.on).toHaveBeenCalledWith("connect", expect.any(Function));
  });

  it("bridges download progress events", () => {
    const dispatchSpy = vi.spyOn(globalThis, "dispatchEvent");
    renderHook(() => useSocketEvents());

    const progressData = { id: 1, progress: 50 };
    handlers["download:progress"](progressData);

    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "download:progress",
        detail: progressData,
      })
    );
  });

  it("bridges download completed events", () => {
    const dispatchSpy = vi.spyOn(globalThis, "dispatchEvent");
    renderHook(() => useSocketEvents());

    const data = { id: 1 };
    handlers["download:completed"](data);

    expect(dispatchSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "download:completed",
        detail: data,
      })
    );
  });

  it("disconnects on unmount", () => {
    const { unmount } = renderHook(() => useSocketEvents());
    unmount();
    expect(mockSocket.disconnect).toHaveBeenCalled();
  });
});
