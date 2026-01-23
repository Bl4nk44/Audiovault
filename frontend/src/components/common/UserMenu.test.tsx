import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStore } from "../../store/useStore";
import UserMenu from "./UserMenu";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("framer-motion", () => ({
  motion: {
    button: ({ children, onClick, ...props }: any) => (
      <button {...props} onClick={onClick} data-testid="user-menu-button">
        {children}
      </button>
    ),
    div: ({ children, onClick, ...props }: any) => (
      <div {...props} onClick={onClick}>
        {children}
      </div>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe("UserMenu", () => {
  const mockUser = {
    id: "u1",
    username: "testuser",
    email: "test@example.com",
  };

  const mockSessions = {
    u1: { user: mockUser },
    u2: { user: { id: "u2", username: "otheruser" } },
  };

  const mockLogout = vi.fn();
  const mockSwitchSession = vi.fn();
  const mockRemoveSession = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as any).mockReturnValue({
      user: mockUser,
      logout: mockLogout,
      sessions: mockSessions,
      switchSession: mockSwitchSession,
      removeSession: mockRemoveSession,
    });
  });

  it("renders user information correctly", () => {
    render(<UserMenu />);
    expect(screen.getByText("testuser")).toBeInTheDocument();
  });

  it("opens and closes the menu", () => {
    render(<UserMenu />);
    const button = screen.getByTestId("user-menu-button");

    // Open
    fireEvent.click(button);
    expect(screen.getByText("test@example.com")).toBeInTheDocument();

    // Close
    fireEvent.click(button);
    expect(screen.queryByText("test@example.com")).not.toBeInTheDocument();
  });

  it("handles logout", () => {
    render(<UserMenu />);
    fireEvent.click(screen.getByTestId("user-menu-button"));

    const logoutBtn = screen.getByText("usermenu.logout");
    fireEvent.click(logoutBtn);

    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith("/login");
  });

  it("handles session switching", () => {
    render(<UserMenu />);
    fireEvent.click(screen.getByTestId("user-menu-button"));

    const otherAccountBtn = screen.getByText("otheruser");
    fireEvent.click(otherAccountBtn);

    expect(mockSwitchSession).toHaveBeenCalledWith("u2");
  });

  it("handles session removal", () => {
    render(<UserMenu />);
    fireEvent.click(screen.getByTestId("user-menu-button"));

    const removeBtn = screen.getByTitle("Remove account");
    fireEvent.click(removeBtn);

    expect(mockRemoveSession).toHaveBeenCalledWith("u2");
  });

  it("navigates to settings", () => {
    render(<UserMenu />);
    fireEvent.click(screen.getByTestId("user-menu-button"));

    const settingsBtn = screen.getByText("usermenu.settings");
    fireEvent.click(settingsBtn);

    expect(mockNavigate).toHaveBeenCalledWith("/settings");
  });

  it("closes when clicking outside", () => {
    render(<UserMenu />);
    fireEvent.click(screen.getByTestId("user-menu-button"));
    expect(screen.getByText("test@example.com")).toBeInTheDocument();

    // Simulate click outside
    act(() => {
      document.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    });

    expect(screen.queryByText("test@example.com")).not.toBeInTheDocument();
  });
});
