import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStore } from "../../store/useStore";
import { VisualizerToggle } from "./VisualizerToggle";

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("lucide-react", () => ({
  Activity: () => <div data-testid="icon-activity" />,
  Check: () => <div data-testid="icon-check" />,
  ChevronDown: () => <div data-testid="icon-chevron-down" />,
}));

describe("VisualizerToggle Component", () => {
  const mockSetShowVisualizer = vi.fn();
  const mockSetVisualizerMode = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as any).mockReturnValue({
      visualizerMode: "classic",
      setVisualizerMode: mockSetVisualizerMode,
    });
  });

  it("renders toggle button", () => {
    render(
      <VisualizerToggle
        showVisualizer={false}
        setShowVisualizer={mockSetShowVisualizer}
        isExpanded={true}
      />
    );
    expect(screen.getByTitle("Toggle Visualizer")).toBeInTheDocument();
  });

  it("toggles visualizer on click", () => {
    render(
      <VisualizerToggle
        showVisualizer={false}
        setShowVisualizer={mockSetShowVisualizer}
        isExpanded={true}
      />
    );
    fireEvent.click(screen.getByTitle("Toggle Visualizer"));
    expect(mockSetShowVisualizer).toHaveBeenCalledWith(true);
  });

  it("opens menu and changes mode", () => {
    render(
      <VisualizerToggle
        showVisualizer={true}
        setShowVisualizer={mockSetShowVisualizer}
        isExpanded={true}
      />
    );

    const menuBtn = screen.getByTestId("icon-chevron-down").closest("button")!;
    fireEvent.click(menuBtn);

    expect(screen.getByText("Visualizer Style")).toBeInTheDocument();

    const waveMode = screen.getByText("Waveform");
    fireEvent.click(waveMode);

    expect(mockSetVisualizerMode).toHaveBeenCalledWith("wave");
  });
});
