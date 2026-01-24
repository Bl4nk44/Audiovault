import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VolumeControl } from "./VolumeControl";

describe("VolumeControl", () => {
  const defaultProps = {
    volume: 0.5,
    setVolume: vi.fn(),
    isExpanded: true,
  };

  it("should render volume button", () => {
    render(<VolumeControl {...defaultProps} />);

    expect(screen.getByRole("button", { name: /mute/i })).toBeTruthy();
  });

  it("should render volume slider", () => {
    render(<VolumeControl {...defaultProps} />);

    expect(screen.getByRole("slider", { name: /volume slider/i })).toBeTruthy();
  });

  it("should show Volume2 icon when not muted", () => {
    render(<VolumeControl {...defaultProps} volume={0.5} />);

    expect(screen.getByRole("button", { name: /mute/i })).toBeTruthy();
  });

  it("should show VolumeX icon when muted", () => {
    render(<VolumeControl {...defaultProps} volume={0} />);

    expect(screen.getByRole("button", { name: /unmute/i })).toBeTruthy();
  });

  it("should mute when volume button is clicked and not muted", async () => {
    const user = userEvent.setup();
    const setVolume = vi.fn();
    render(<VolumeControl {...defaultProps} volume={0.5} setVolume={setVolume} />);

    await user.click(screen.getByRole("button", { name: /mute/i }));

    expect(setVolume).toHaveBeenCalledWith(0);
  });

  it("should unmute when volume button is clicked and muted", async () => {
    const user = userEvent.setup();
    const setVolume = vi.fn();
    render(<VolumeControl {...defaultProps} volume={0} setVolume={setVolume} />);

    await user.click(screen.getByRole("button", { name: /unmute/i }));

    expect(setVolume).toHaveBeenCalledWith(1);
  });

  it("should call setVolume when slider is changed", () => {
    const setVolume = vi.fn();
    render(<VolumeControl {...defaultProps} setVolume={setVolume} />);

    const slider = screen.getByRole("slider", { name: /volume slider/i });
    fireEvent.change(slider, { target: { value: "0.8" } });

    expect(setVolume).toHaveBeenCalledWith(0.8);
  });

  it("should set correct slider value", () => {
    render(<VolumeControl {...defaultProps} volume={0.75} />);

    const slider = screen.getByRole("slider", {
      name: /volume slider/i,
    }) as HTMLInputElement;
    expect(slider.value).toBe("0.75");
  });

  it("should be hidden on mobile when not expanded", () => {
    const { container } = render(<VolumeControl {...defaultProps} isExpanded={false} />);

    expect(container.firstChild).toHaveClass("hidden");
    expect(container.firstChild).toHaveClass("md:flex");
  });

  it("should be visible when expanded", () => {
    const { container } = render(<VolumeControl {...defaultProps} isExpanded={true} />);

    expect(container.firstChild).not.toHaveClass("hidden");
  });
});
