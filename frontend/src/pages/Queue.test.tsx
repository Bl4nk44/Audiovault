import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Queue from "./Queue";

// Mock child components
vi.mock("../components/queue/DownloadQueue", () => ({
  default: () => <div data-testid="download-queue">Download Queue Content</div>,
}));

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className }: any) => <div className={className}>{children}</div>,
  },
}));

describe("Queue Page", () => {
  it("renders queue header and component", () => {
    render(<Queue />);

    expect(screen.getByText("Download Queue")).toBeInTheDocument();
    expect(screen.getByText("Manage your active downloads and history.")).toBeInTheDocument();
    expect(screen.getByTestId("download-queue")).toBeInTheDocument();
  });
});
