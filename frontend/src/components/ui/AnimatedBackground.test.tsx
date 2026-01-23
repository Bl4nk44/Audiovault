import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnimatedBackground } from "./AnimatedBackground";

describe("AnimatedBackground", () => {
  it("renders without crashing", () => {
    const { container } = render(<AnimatedBackground />);
    expect(container.firstChild).toHaveClass("fixed inset-0");
  });
});
