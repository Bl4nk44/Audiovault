import { describe, it, expect } from "vitest";
import { formatTime } from "./format";

describe("formatTime", () => {
  it('should format 0 seconds as "0:00"', () => {
    expect(formatTime(0)).toBe("0:00");
  });

  it('should format 59 seconds as "0:59"', () => {
    expect(formatTime(59)).toBe("0:59");
  });

  it('should format 60 seconds as "1:00"', () => {
    expect(formatTime(60)).toBe("1:00");
  });

  it('should format 90 seconds as "1:30"', () => {
    expect(formatTime(90)).toBe("1:30");
  });

  it('should format 3661 seconds as "61:01"', () => {
    expect(formatTime(3661)).toBe("61:01");
  });

  it("should handle decimal values by flooring", () => {
    expect(formatTime(65.7)).toBe("1:05");
  });

  it("should pad single digit seconds with leading zero", () => {
    expect(formatTime(5)).toBe("0:05");
    expect(formatTime(65)).toBe("1:05");
  });

  it('should return "0:00" for NaN input', () => {
    expect(formatTime(NaN)).toBe("0:00");
  });
});
