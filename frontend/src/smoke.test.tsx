// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, it, expect } from "vitest";

describe("React Router Smoke Test", () => {
  it("renders a simple route", () => {
    render(
      <MemoryRouter initialEntries={["/test"]}>
        <Routes>
          <Route
            path="/test"
            element={<div data-testid="test-route">Router Works</div>}
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId("test-route")).toBeTruthy();
    expect(screen.getByText("Router Works")).toBeTruthy();
  });
});
