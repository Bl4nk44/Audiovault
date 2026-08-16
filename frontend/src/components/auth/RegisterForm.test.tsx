import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RegisterForm from "./RegisterForm";
import { BrowserRouter } from "react-router-dom";
import { register as mockRegister } from "../../services/auth";
import { notify as mockToast } from "../../utils/notify";

// Mocks
vi.mock("../../services/auth", () => ({
  register: vi.fn(),
}));

vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", async () => {
  const React = await import("react");
  const dummy = (tag: string) =>
    React.forwardRef((props: any, ref: any) => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { whileHover, whileTap, whileFocus, initial, variants, transition, ...rest } = props;
      return React.createElement(tag, { ...rest, ref });
    });

  return {
    motion: {
      input: dummy("input"),
      div: dummy("div"),
      button: dummy("button"),
      span: dummy("span"),
      form: dummy("form"),
    },
    AnimatePresence: ({ children }: any) => children,
  };
});

describe("RegisterForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderForm = () => {
    return render(
      <BrowserRouter>
        <RegisterForm />
      </BrowserRouter>
    );
  };

  it("renders all form fields", () => {
    renderForm();
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirm Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create Account/i })).toBeInTheDocument();
  });

  it("shows validation errors for empty fields on submit", async () => {
    renderForm();
    fireEvent.click(screen.getByRole("button", { name: /Create Account/i }));

    await waitFor(() => {
      expect(screen.getByText(/Username is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Password is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Please confirm your password/i)).toBeInTheDocument();
    });
  });

  it("shows error when passwords do not match", async () => {
    renderForm();

    fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), { target: { value: "mismatch" } });
    fireEvent.click(screen.getByRole("button", { name: /Create Account/i }));

    await waitFor(() => {
      expect(screen.getByText(/Your passwords do not match/i)).toBeInTheDocument();
    });
  });

  it("calls register API and navigates on success", async () => {
    vi.mocked(mockRegister).mockResolvedValue({ status: "success" });
    renderForm();

    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: "testuser" } });
    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), { target: { value: "password123" } });

    fireEvent.click(screen.getByRole("button", { name: /Create Account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        username: "testuser",
        email: "test@example.com",
        // eslint-disable-next-line sonarjs/no-hardcoded-passwords -- test fixture, not a real credential
        password: "password123",
      });
      expect(mockToast.success).toHaveBeenCalledWith("Registration successful! Please login.");
      expect(mockNavigate).toHaveBeenCalledWith("/login");
    });
  });

  it("shows toast error on API failure", async () => {
    vi.mocked(mockRegister).mockRejectedValue({
      response: { data: { detail: "User already exists" } }
    });
    renderForm();

    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: "testuser" } });
    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText(/^Password$/i), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), { target: { value: "password123" } });

    fireEvent.click(screen.getByRole("button", { name: /Create Account/i }));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("User already exists");
    });
  });
});
