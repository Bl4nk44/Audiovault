import axios from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Robust hoisting for interceptors
const { captured } = vi.hoisted(() => ({
  captured: { req: null as any, err: null as any },
}));

vi.mock("axios", async (importOriginal) => {
  const actual = await importOriginal<any>();

  const mockCreate = vi.fn().mockImplementation(() => {
    const instance = vi.fn().mockResolvedValue({ data: "ok" }) as any;
    instance.interceptors = {
      request: {
        use: vi.fn((fn) => {
          captured.req = fn;
        }),
      },
      response: {
        use: vi.fn((_s, e) => {
          captured.err = e;
        }),
      },
    };
    instance.defaults = { headers: { common: {} } };
    instance.get = vi.fn().mockResolvedValue({ data: "ok" });
    instance.post = vi.fn().mockResolvedValue({ data: "ok" });
    return instance;
  });

  return {
    ...actual,
    default: {
      ...actual.default,
      create: mockCreate,
      post: vi.fn().mockResolvedValue({ data: "ok" }),
    },
  };
});

// Import after mock
import { injectStore, resetInterceptorState } from "./api";

describe("API Service Interceptors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetInterceptorState();
  });

  it("should have captured interceptors", () => {
    expect(captured.req).toBeTypeOf("function");
    expect(captured.err).toBeTypeOf("function");
  });

  it("request interceptor should add token", () => {
    const storage = globalThis.localStorage as any;
    storage.getItem.mockReturnValue("abc");

    const config = { headers: {} } as any;
    const result = captured.req(config);
    expect(result.headers.Authorization).toBe("Bearer abc");
  });

  it("response interceptor should handle 401 refresh", async () => {
    const mockSetTokens = vi.fn();
    injectStore({
      getState: () => ({
        logout: vi.fn(),
        setTokens: mockSetTokens,
      }),
    } as any);

    const storage = globalThis.localStorage as any;
    storage.getItem.mockImplementation((key: string) => {
      if (key === "refresh_token") return "refresh-me";
      return null;
    });

    vi.spyOn(axios, "post").mockResolvedValue({
      data: { access_token: "new-a", refresh_token: "new-r" },
    });

    const error = {
      response: { status: 401 },
      config: { headers: {}, _retry: false },
    } as any;

    const result = await captured.err(error);

    expect(axios.post).toHaveBeenCalled();
    expect(result.data).toBe("ok");
  });

  it("response interceptor should handle 401 logout if no refresh token", async () => {
    const mockLogout = vi.fn();
    injectStore({
      getState: () => ({
        logout: mockLogout,
        setTokens: vi.fn(),
      }),
    } as any);

    const storage = globalThis.localStorage as any;
    storage.getItem.mockReturnValue(null);

    const error = {
      response: { status: 401 },
      config: { headers: {}, _retry: false },
    } as any;

    await expect(captured.err(error)).rejects.toEqual(error);
    expect(mockLogout).toHaveBeenCalled();
  });

  it("response interceptor should handle refresh failure", async () => {
    const storage = globalThis.localStorage as any;
    storage.getItem.mockReturnValue("bad-token");
    vi.spyOn(axios, "post").mockRejectedValue(new Error("Refresh failed"));

    const mockLogout = vi.fn();
    injectStore({ getState: () => ({ logout: mockLogout, setTokens: vi.fn() }) } as any);

    const error = {
      response: { status: 401 },
      config: { headers: {}, _retry: false },
    } as any;

    await expect(captured.err(error)).rejects.toThrow("Refresh failed");
    expect(mockLogout).toHaveBeenCalled();
  });
});
