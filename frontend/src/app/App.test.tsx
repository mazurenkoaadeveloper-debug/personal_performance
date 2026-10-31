import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { App } from "./App";


test("shows the product shell and primary navigation", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", { name: "GitLab Developer Activity Analytics" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Разработчики")).toBeInTheDocument();
  expect(screen.getByText("Синхронизация")).toBeInTheDocument();
});
