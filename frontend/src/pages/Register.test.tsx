import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Register from "./Register";

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div className={className}>{children}</div>
    ),
    p: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <p className={className}>{children}</p>
    ),
    h1: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <h1 className={className}>{children}</h1>
    ),
  },
}));

// Mock RegisterForm
vi.mock("../components/auth/RegisterForm", () => ({
  default: () => <div data-testid="register-form">RegisterForm Mock</div>,
}));

// Mock registration status hook (mutable so tests can flip the flag)
const regState = vi.hoisted(() => ({ enabled: true }));
vi.mock("../hooks/useRegistrationStatus", () => ({
  useRegistrationStatus: () => ({ data: { enabled: regState.enabled }, isLoading: false }),
}));

describe("Register", () => {
  const renderRegister = () => {
    return render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    );
  };

  it('should render "Join Audiovault" heading', () => {
    renderRegister();

    expect(screen.getByRole("heading", { name: /join audiovault/i })).toBeTruthy();
  });

  it("should render description text", () => {
    renderRegister();

    expect(screen.getByText("Create an account to start downloading")).toBeTruthy();
  });

  it("should render RegisterForm component", () => {
    renderRegister();

    expect(screen.getByTestId("register-form")).toBeTruthy();
  });

  it("should render link to login page", () => {
    renderRegister();

    const loginLink = screen.getByRole("link", { name: /sign in/i });
    expect(loginLink).toBeTruthy();
    expect(loginLink.getAttribute("href")).toBe("/login");
  });

  it('should display "Already have an account?" text', () => {
    renderRegister();

    expect(screen.getByText(/Already have an account/)).toBeTruthy();
  });

  it("redirects to /login when registration is disabled", () => {
    regState.enabled = false;
    render(
      <MemoryRouter initialEntries={["/register"]}>
        <Routes>
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Login Page")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: /join audiovault/i })).toBeNull();
  });

  afterEach(() => {
    regState.enabled = true;
  });
});
