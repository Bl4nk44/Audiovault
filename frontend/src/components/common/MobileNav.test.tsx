import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import MobileNav from "./MobileNav";

// Mock framer-motion
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className, ...props }: any) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
  },
}));

describe("MobileNav", () => {
  it("renders all navigation items", () => {
    render(
      <MemoryRouter>
        <MobileNav />
      </MemoryRouter>
    );
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Search")).toBeInTheDocument();
    expect(screen.getByText("Library")).toBeInTheDocument();
    expect(screen.getByText("Queue")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("highlights active link", () => {
    render(
      <MemoryRouter initialEntries={["/search"]}>
        <MobileNav />
      </MemoryRouter>
    );

    // The active link should have the primary color class
    const searchLink = screen.getByText("Search").closest("a");
    expect(searchLink).toHaveClass("text-primary");

    const homeLink = screen.getByText("Home").closest("a");
    expect(homeLink).not.toHaveClass("text-primary");
  });

  it("contains a link to the Discovery page", () => {
    render(
      <MemoryRouter>
        <MobileNav />
      </MemoryRouter>
    );
    expect(screen.getByRole("link", { name: /discover/i })).toHaveAttribute(
      "href",
      "/recommendations"
    );
  });
});
