import { describe, it, expect } from "vitest";
import { isValidImageUrl } from "./validation";

describe("isValidImageUrl", () => {
  describe("valid URLs", () => {
    it("should return true for http URLs", () => {
      expect(isValidImageUrl("http://example.com/image.jpg")).toBe(true);
    });

    it("should return true for https URLs", () => {
      expect(isValidImageUrl("https://example.com/image.png")).toBe(true);
    });

    it("should return true for URLs with query parameters", () => {
      expect(isValidImageUrl("https://cdn.example.com/img.jpg?size=large&quality=high")).toBe(true);
    });

    it("should return true for relative paths starting with /", () => {
      expect(isValidImageUrl("/static/images/default.png")).toBe(true);
    });

    it("should return true for complex CDN URLs", () => {
      expect(isValidImageUrl("https://i.scdn.co/image/ab67616d0000b273123456789abcdef")).toBe(true);
    });
  });

  describe("invalid URLs", () => {
    it("should return false for null", () => {
      expect(isValidImageUrl(null)).toBe(false);
    });

    it("should return false for undefined", () => {
      expect(isValidImageUrl(undefined)).toBe(false);
    });

    it("should return false for empty string", () => {
      expect(isValidImageUrl("")).toBe(false);
    });

    it("should return false for javascript: protocol (XSS prevention)", () => {
      expect(isValidImageUrl("javascript:alert(1)")).toBe(false);
    });

    it("should return false for data: URLs", () => {
      expect(isValidImageUrl("data:image/png;base64,iVBORw0KGgo=")).toBe(false);
    });

    it("should return false for file: protocol", () => {
      expect(isValidImageUrl("file:///etc/passwd")).toBe(false);
    });

    it("should return false for ftp: protocol", () => {
      expect(isValidImageUrl("ftp://example.com/image.jpg")).toBe(false);
    });

    it("should return false for malformed URLs (not starting with /)", () => {
      expect(isValidImageUrl("not-a-valid-url")).toBe(false);
    });

    it("should return false for relative paths without leading /", () => {
      expect(isValidImageUrl("images/pic.jpg")).toBe(false);
    });
  });
});
