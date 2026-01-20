import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Register from "./Register";

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({
      children,
      className,
    }: {
      children: React.ReactNode;
      className?: string;
    }) => <div className={className}>{children}</div>,
    p: ({
      children,
      className,
    }: {
      children: React.ReactNode;
      className?: string;
    }) => <p className={className}>{children}</p>,
    h1: ({
      children,
      className,
    }: {
      children: React.ReactNode;
      className?: string;
    }) => <h1 className={className}>{children}</h1>,
  },
}));

// Mock RegisterForm
vi.mock("../components/auth/RegisterForm", () => ({
  default: () => <div data-testid="register-form">RegisterForm Mock</div>,
}));

describe("Register", () => {
  const renderRegister = () => {
    return render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>,
    );
  };

  it('should render "Join Audiovault" heading', () => {
    renderRegister();

    expect(
      screen.getByRole("heading", { name: /join audiovault/i }),
    ).toBeTruthy();
  });

  it("should render description text", () => {
    renderRegister();

    expect(
      screen.getByText("Create an account to start downloading"),
    ).toBeTruthy();
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
});
