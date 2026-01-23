import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Logo from "./Logo";

describe("Logo", () => {
  it("renders with text by default", () => {
    render(<Logo />);
    expect(screen.getByText("Audiovault")).toBeInTheDocument();
  });

  it("hides text when showText is false", () => {
    render(<Logo showText={false} />);
    expect(screen.queryByText("Audiovault")).not.toBeInTheDocument();
  });

  it("applies correct size classes", () => {
    const { container } = render(<Logo size="xl" />);
    const logoBox = container.querySelector(".rounded-xl");
    expect(logoBox).toHaveClass("w-32 h-32");
  });
});
