/* eslint-disable */
import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAudioVisualizer } from "./useAudioVisualizer";

const TestComponent = ({ track, isPlaying, mode, audioRef }: any) => {
  const canvasRef = useAudioVisualizer(track, isPlaying, audioRef, mode);
  return <canvas ref={canvasRef} data-testid="visualizer-canvas" width={800} height={400} />;
};

describe("useAudioVisualizer - Modes", () => {
  let mockAudioContext: any;
  let mockAnalyser: any;
  let mockSource: any;
  let mockCtx: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockCtx = {
      fillStyle: "",
      fillRect: vi.fn(),
      beginPath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      stroke: vi.fn(),
      save: vi.fn(),
      restore: vi.fn(),
      translate: vi.fn(),
      rotate: vi.fn(),
      arc: vi.fn(),
      fill: vi.fn(),
      clearRect: vi.fn(),
      createLinearGradient: vi.fn().mockReturnValue({ addColorStop: vi.fn() }),
      createRadialGradient: vi.fn().mockReturnValue({ addColorStop: vi.fn() }),
    };

    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(mockCtx as any);

    mockAnalyser = {
      smoothingTimeConstant: 0.8,
      fftSize: 512,
      frequencyBinCount: 256,
      getByteFrequencyData: vi.fn((arr) => {
        // Fill with dummy data
        for (let i = 0; i < arr.length; i++) arr[i] = 128;
      }),
      getByteTimeDomainData: vi.fn(),
      connect: vi.fn(),
    };

    mockSource = { connect: vi.fn() };

    mockAudioContext = {
      createAnalyser: vi.fn().mockReturnValue(mockAnalyser),
      createMediaElementSource: vi.fn().mockReturnValue(mockSource),
      destination: {},
      state: "suspended",
      resume: vi.fn().mockResolvedValue(undefined),
    };

    const AudioContextMock = vi.fn(function () {
      return mockAudioContext;
    });
    vi.stubGlobal("AudioContext", AudioContextMock);

    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      getPropertyValue: vi.fn().mockImplementation((prop) => {
        if (prop === "--primary") return "250 100% 50%";
        return "";
      }),
    } as any);

    // Mock requestAnimationFrame to run once
    vi.stubGlobal(
      "requestAnimationFrame",
      vi.fn((_cb) => {
        // Don't loop infinitely in tests, just run once if needed
      })
    );
  });

  const track = { id: "t1" };
  const mockAudioRef = { current: { crossOrigin: "", play: vi.fn(), pause: vi.fn() } as any };

  it("renders circle mode", async () => {
    render(<TestComponent track={track} isPlaying={true} mode="circle" audioRef={mockAudioRef} />);
    // Initial render sets the loop, but we need to trigger the render function
    // Since requestAnimationFrame is mocked, we can't easily test the internal render
    // without exposing it or using a more complex mock.
    // However, the test covers the initialization path.
    expect(mockAudioContext.createAnalyser).toHaveBeenCalled();
  });

  it("renders particles mode", () => {
    render(
      <TestComponent track={track} isPlaying={true} mode="particles" audioRef={mockAudioRef} />
    );
    expect(mockAudioContext.createAnalyser).toHaveBeenCalled();
  });

  it("renders glow mode", () => {
    render(<TestComponent track={track} isPlaying={true} mode="glow" audioRef={mockAudioRef} />);
    expect(mockAudioContext.createAnalyser).toHaveBeenCalled();
  });

  it("handles track stop", () => {
    const { rerender } = render(
      <TestComponent track={track} isPlaying={true} mode="classic" audioRef={mockAudioRef} />
    );
    rerender(
      <TestComponent track={null} isPlaying={false} mode="classic" audioRef={mockAudioRef} />
    );
    expect(mockCtx.clearRect).toHaveBeenCalled();
  });
});
