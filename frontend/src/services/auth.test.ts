import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "./api";
import * as authService from "./auth";

// Mock the api instance
vi.mock("./api", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe("Auth Service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("should call api.post with login credentials and return data", async () => {
      const credentials = { username: "test", password: "password" };
      const mockResponse = { data: { token: "xyz", user: { id: 1 } } };
      (api.post as any).mockResolvedValue(mockResponse);

      const result = await authService.login(credentials);

      expect(api.post).toHaveBeenCalledWith("/auth/login", credentials);
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe("register", () => {
    it("should call api.post with register data and return data", async () => {
      const data = { username: "test", password: "password", email: "test@test.com" };
      const mockResponse = { data: { id: 1, username: "test" } };
      (api.post as any).mockResolvedValue(mockResponse);

      const result = await authService.register(data);

      expect(api.post).toHaveBeenCalledWith("/auth/register", data);
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe("getMe", () => {
    it("should call api.get with /auth/me and return data", async () => {
      const mockResponse = { data: { id: 1, username: "test" } };
      (api.get as any).mockResolvedValue(mockResponse);

      const result = await authService.getMe();

      expect(api.get).toHaveBeenCalledWith("/auth/me");
      expect(result).toEqual(mockResponse.data);
    });
  });
});
