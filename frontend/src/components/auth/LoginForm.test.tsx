import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginForm from "./LoginForm";

// Mocks
const mockLogin = vi.fn();
const mockGetMe = vi.fn();
const mockAddSession = vi.fn();
const mockSetTokens = vi.fn();
const mockNavigate = vi.fn();
const mockSuccessToast = vi.fn();
const mockErrorToast = vi.fn();

vi.mock("../../services/auth", () => ({
  login: (creds: any) => mockLogin(creds),
  getMe: () => mockGetMe(),
}));

vi.mock("../../store/useStore", () => ({
  useStore: () => ({
    addSession: mockAddSession,
    setTokens: mockSetTokens,
  }),
}));

vi.mock("../../utils/notify", () => ({
  notify: {
    success: (msg: string) => mockSuccessToast(msg),
    error: (msg: string) => mockErrorToast(msg),
    dismiss: vi.fn(),
  },
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () => {
    render(
      <BrowserRouter>
        <LoginForm />
      </BrowserRouter>
    );
  };

  it("should render login form", () => {
    renderComponent();
    expect(screen.getByLabelText(/username or email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("should validate required fields", async () => {
    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/username or email is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("should handle successful login", async () => {
    mockLogin.mockResolvedValueOnce({
      access_token: "access_token_123",
      refresh_token: "refresh_token_123",
    });
    mockGetMe.mockResolvedValueOnce({ id: "user_1", username: "testuser" });

    renderComponent();

    fireEvent.change(screen.getByLabelText(/username or email/i), {
      target: { value: "testuser" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "password123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: "testuser",
        // eslint-disable-next-line sonarjs/no-hardcoded-passwords -- test fixture, not a real credential
        password: "password123",
      });
    });

    await waitFor(() => {
      expect(mockSetTokens).toHaveBeenCalledWith("access_token_123", "refresh_token_123");
      expect(mockGetMe).toHaveBeenCalled();
      expect(mockAddSession).toHaveBeenCalledWith(
        { id: "user_1", username: "testuser" },
        "access_token_123",
        "refresh_token_123"
      );
      expect(mockSuccessToast).toHaveBeenCalledWith("Logged in successfully");
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  it("should handle login error", async () => {
    mockLogin.mockRejectedValueOnce({
      response: {
        data: { detail: "Invalid credentials" },
      },
    });

    renderComponent();

    fireEvent.change(screen.getByLabelText(/username or email/i), {
      target: { value: "wrong" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "wrong" },
    });

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockErrorToast).toHaveBeenCalledWith("Invalid credentials");
    });
    expect(mockAddSession).not.toHaveBeenCalled();
  });
});
