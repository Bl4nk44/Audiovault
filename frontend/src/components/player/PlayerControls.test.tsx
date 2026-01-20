import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlayerControls } from "./PlayerControls";

describe("PlayerControls", () => {
  const defaultProps = {
    isPlaying: false,
    togglePlay: vi.fn(),
    nextTrack: vi.fn(),
    prevTrack: vi.fn(),
    isExpanded: false,
  };

  it("should render all control buttons", () => {
    render(<PlayerControls {...defaultProps} />);

    expect(
      screen.getByRole("button", { name: /previous track/i }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /play/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /next track/i })).toBeTruthy();
  });

  it("should show Play button when not playing", () => {
    render(<PlayerControls {...defaultProps} isPlaying={false} />);

    expect(screen.getByRole("button", { name: /play/i })).toBeTruthy();
  });

  it("should show Pause button when playing", () => {
    render(<PlayerControls {...defaultProps} isPlaying={true} />);

    expect(screen.getByRole("button", { name: /pause/i })).toBeTruthy();
  });

  it("should call togglePlay when play button is clicked", async () => {
    const user = userEvent.setup();
    const togglePlay = vi.fn();
    render(<PlayerControls {...defaultProps} togglePlay={togglePlay} />);

    await user.click(screen.getByRole("button", { name: /play/i }));

    expect(togglePlay).toHaveBeenCalledTimes(1);
  });

  it("should call prevTrack when previous button is clicked", async () => {
    const user = userEvent.setup();
    const prevTrack = vi.fn();
    render(<PlayerControls {...defaultProps} prevTrack={prevTrack} />);

    await user.click(screen.getByRole("button", { name: /previous track/i }));

    expect(prevTrack).toHaveBeenCalledTimes(1);
  });

  it("should call nextTrack when next button is clicked", async () => {
    const user = userEvent.setup();
    const nextTrack = vi.fn();
    render(<PlayerControls {...defaultProps} nextTrack={nextTrack} />);

    await user.click(screen.getByRole("button", { name: /next track/i }));

    expect(nextTrack).toHaveBeenCalledTimes(1);
  });

  it("should apply expanded styles when isExpanded is true", () => {
    const { container } = render(
      <PlayerControls {...defaultProps} isExpanded={true} />,
    );

    // Play button should have larger size class in expanded mode
    const playButton = screen.getByRole("button", { name: /play/i });
    expect(playButton).toHaveClass("w-16");
    expect(playButton).toHaveClass("h-16");
  });

  it("should apply collapsed styles when isExpanded is false", () => {
    render(<PlayerControls {...defaultProps} isExpanded={false} />);

    const playButton = screen.getByRole("button", { name: /play/i });
    expect(playButton).toHaveClass("w-10");
    expect(playButton).toHaveClass("h-10");
  });
});
