import { fireEvent, render, screen } from "@testing-library/react";
import { toast } from "react-hot-toast";
import { describe, expect, it, vi } from "vitest";
import { UpdateToast } from "./UpdateToast";

vi.mock("react-hot-toast", () => ({
  toast: {
    dismiss: vi.fn(),
  },
}));

describe("UpdateToast", () => {
  const mockToast = { id: "t1" } as any;
  const mockUrl = "http://example.com";

  it("renders correctly", () => {
    render(<UpdateToast t={mockToast} text="Update info" url={mockUrl} />);
    expect(screen.getByText("New Version Available! 🚀")).toBeInTheDocument();
    expect(screen.getByText("Update info")).toBeInTheDocument();
  });

  it("calls dismiss on 'View' click", () => {
    render(<UpdateToast t={mockToast} text="Update info" url={mockUrl} />);
    fireEvent.click(screen.getByText("View"));
    expect(toast.dismiss).toHaveBeenCalledWith("t1");
  });

  it("calls dismiss on 'Dismiss' click", () => {
    render(<UpdateToast t={mockToast} text="Update info" url={mockUrl} />);
    fireEvent.click(screen.getByText("Dismiss"));
    expect(toast.dismiss).toHaveBeenCalledWith("t1");
  });
});
