import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStore } from "../../store/useStore";
import NotificationCenter from "./NotificationCenter";

// Mock store
const mockMarkAllAsRead = vi.fn();
const mockClearNotifications = vi.fn();
const mockRemoveNotification = vi.fn();

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className, onClick }: any) => (
      <div className={className} onClick={onClick}>
        {children}
      </div>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock lucide-react
vi.mock("lucide-react", () => ({
  X: () => <div data-testid="icon-x" />,
  CheckCircle: () => <div data-testid="icon-check-circle" />,
  AlertCircle: () => <div data-testid="icon-alert-circle" />,
  Info: () => <div data-testid="icon-info" />,
  AlertTriangle: () => <div data-testid="icon-alert-triangle" />,
  Trash2: () => <div data-testid="icon-trash" />,
  Bell: () => <div data-testid="icon-bell" />,
}));

describe("NotificationCenter Component", () => {
  const mockNotifications = [
    { id: "1", type: "success", message: "Success msg", timestamp: Date.now(), read: false },
    { id: "2", type: "error", message: "Error msg", timestamp: Date.now(), read: true },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as any).mockReturnValue({
      notifications: mockNotifications,
      markAllAsRead: mockMarkAllAsRead,
      clearNotifications: mockClearNotifications,
      removeNotification: mockRemoveNotification,
      user: { preferences: { language: "en" } },
    });
  });

  it("renders only when open", () => {
    const { rerender } = render(<NotificationCenter isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByText("notifications.title")).not.toBeInTheDocument();

    rerender(<NotificationCenter isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByText("notifications.title")).toBeInTheDocument();
  });

  it("renders notification list", () => {
    render(<NotificationCenter isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByText("Success msg")).toBeInTheDocument();
    expect(screen.getByText("Error msg")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument(); // Count badge
  });

  it("handles actions", () => {
    render(<NotificationCenter isOpen={true} onClose={vi.fn()} />);

    const markAllBtn = screen.getByText("notifications.markAllRead");
    fireEvent.click(markAllBtn);
    expect(mockMarkAllAsRead).toHaveBeenCalled();

    const clearBtn = screen.getByTitle("notifications.clearAll");
    fireEvent.click(clearBtn);
    expect(mockClearNotifications).toHaveBeenCalled();
  });
});
