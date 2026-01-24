import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import NotFound from "./NotFound";

describe("NotFound", () => {
  const renderNotFound = () => {
    return render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>
    );
  };

  it("should render 404 heading", () => {
    renderNotFound();

    expect(screen.getByText("404")).toBeTruthy();
  });

  it('should display "page not found" message in Polish', () => {
    renderNotFound();

    expect(screen.getByText("Strona nie została znaleziona")).toBeTruthy();
  });

  it("should display descriptive text", () => {
    renderNotFound();

    expect(screen.getByText(/Wygląda na to, że zabłądziłeś/)).toBeTruthy();
  });

  it("should render home link", () => {
    renderNotFound();

    const homeLink = screen.getByRole("link", {
      name: /Wróć do strony głównej/i,
    });
    expect(homeLink).toBeTruthy();
    expect(homeLink.getAttribute("href")).toBe("/");
  });

  it("should render AlertCircle icon", () => {
    renderNotFound();

    // Lucide icons render as SVG
    const container = document.querySelector(".animate-pulse");
    expect(container).toBeTruthy();
  });
});
