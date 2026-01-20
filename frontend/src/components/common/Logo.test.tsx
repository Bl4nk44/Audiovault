import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Logo from "./Logo";

describe("Logo", () => {
  it("should render logo image", () => {
    render(<Logo />);

    const img = screen.getByAltText("Audiovault");
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe("/logo.png");
  });

  it("should show text by default", () => {
    render(<Logo />);

    expect(screen.getByText("Audiovault")).toBeTruthy();
  });

  it("should hide text when showText is false", () => {
    render(<Logo showText={false} />);

    expect(screen.queryByText("Audiovault")).toBeNull();
  });

  it("should apply custom className", () => {
    const { container } = render(<Logo className="custom-class" />);

    expect(container.firstChild).toHaveClass("custom-class");
  });

  describe("sizes", () => {
    it("should apply sm size classes", () => {
      const { container } = render(<Logo size="sm" />);

      expect(container.querySelector(".w-8")).toBeTruthy();
      expect(container.querySelector(".h-8")).toBeTruthy();
    });

    it("should apply md size classes (default)", () => {
      const { container } = render(<Logo />);

      expect(container.querySelector(".w-12")).toBeTruthy();
      expect(container.querySelector(".h-12")).toBeTruthy();
    });

    it("should apply lg size classes", () => {
      const { container } = render(<Logo size="lg" />);

      expect(container.querySelector(".w-20")).toBeTruthy();
      expect(container.querySelector(".h-20")).toBeTruthy();
    });

    it("should apply xl size classes", () => {
      const { container } = render(<Logo size="xl" />);

      expect(container.querySelector(".w-32")).toBeTruthy();
      expect(container.querySelector(".h-32")).toBeTruthy();
    });
  });

  describe("text sizes", () => {
    it("should apply correct text size for sm", () => {
      render(<Logo size="sm" />);

      const text = screen.getByText("Audiovault");
      expect(text).toHaveClass("text-lg");
    });

    it("should apply correct text size for lg", () => {
      render(<Logo size="lg" />);

      const text = screen.getByText("Audiovault");
      expect(text).toHaveClass("text-4xl");
    });
  });
});
