import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProgressBar } from "./ProgressBar";

describe("ProgressBar", () => {
  const defaultProps = {
    currentTime: 60,
    duration: 180,
    onSeek: vi.fn(),
    isExpanded: true,
  };

  it("should render current time", () => {
    render(<ProgressBar {...defaultProps} />);

    expect(screen.getByText("1:00")).toBeTruthy();
  });

  it("should render duration", () => {
    render(<ProgressBar {...defaultProps} />);

    expect(screen.getByText("3:00")).toBeTruthy();
  });

  it("should render seek slider", () => {
    render(<ProgressBar {...defaultProps} />);

    expect(screen.getByRole("slider", { name: /seek slider/i })).toBeTruthy();
  });

  it("should set correct slider value", () => {
    render(<ProgressBar {...defaultProps} currentTime={90} />);

    const slider = screen.getByRole("slider", {
      name: /seek slider/i,
    }) as HTMLInputElement;
    expect(slider.value).toBe("90");
  });

  it("should call onSeek when slider is changed", () => {
    const onSeek = vi.fn();
    render(<ProgressBar {...defaultProps} onSeek={onSeek} />);

    const slider = screen.getByRole("slider", { name: /seek slider/i });
    fireEvent.change(slider, { target: { value: "120" } });

    expect(onSeek).toHaveBeenCalledWith(120);
  });

  it("should handle zero duration", () => {
    render(<ProgressBar {...defaultProps} duration={0} currentTime={0} />);

    // Both current time and duration show 0:00
    const timeElements = screen.getAllByText("0:00");
    expect(timeElements).toHaveLength(2);
  });

  it("should be hidden on mobile when not expanded", () => {
    const { container } = render(<ProgressBar {...defaultProps} isExpanded={false} />);

    expect(container.firstChild).toHaveClass("hidden");
    expect(container.firstChild).toHaveClass("md:flex");
  });

  it("should be visible when expanded", () => {
    const { container } = render(<ProgressBar {...defaultProps} isExpanded={true} />);

    expect(container.firstChild).not.toHaveClass("hidden");
  });

  it("should format time correctly for various values", () => {
    const { rerender } = render(<ProgressBar {...defaultProps} currentTime={5} duration={65} />);

    expect(screen.getByText("0:05")).toBeTruthy();
    expect(screen.getByText("1:05")).toBeTruthy();

    rerender(<ProgressBar {...defaultProps} currentTime={3661} duration={7200} />);
    expect(screen.getByText("61:01")).toBeTruthy();
  });
});
