import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "./Login";

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <div className={className}>{children}</div>
    ),
    p: ({ children, className }: { children: React.ReactNode; className?: string }) => (
      <p className={className}>{children}</p>
    ),
  },
}));

// Mock LoginForm
vi.mock("../components/auth/LoginForm", () => ({
  default: () => <div data-testid="login-form">LoginForm Mock</div>,
}));

// Mock Logo
vi.mock("../components/common/Logo", () => ({
  default: () => <div data-testid="logo">Logo Mock</div>,
}));

describe("Login", () => {
  const renderLogin = () => {
    return render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
  };

  it("should render Logo component", () => {
    renderLogin();

    expect(screen.getByTestId("logo")).toBeTruthy();
  });

  it("should render sign in message", () => {
    renderLogin();

    expect(screen.getByText("Sign in to continue to Audiovault")).toBeTruthy();
  });

  it("should render LoginForm component", () => {
    renderLogin();

    expect(screen.getByTestId("login-form")).toBeTruthy();
  });

  it("should render link to register page", () => {
    renderLogin();

    const registerLink = screen.getByRole("link", { name: /create account/i });
    expect(registerLink).toBeTruthy();
    expect(registerLink.getAttribute("href")).toBe("/register");
  });

  it('should display "Don\'t have an account?" text', () => {
    renderLogin();

    expect(screen.getByText(/Don't have an account/)).toBeTruthy();
  });
});
