import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { ThemeModeProvider, useThemeMode } from "../ThemeModeProvider";

function ThemeProbe() {
  const { mode, resolvedMode, setMode } = useThemeMode();
  return (
    <>
      <p>{`${mode}:${resolvedMode}`}</p>
      <button onClick={() => setMode("dark")} type="button">Use dark theme</button>
    </>
  );
}

afterEach(() => {
  window.localStorage.removeItem("presidio-color-scheme");
  document.documentElement.classList.remove("dark");
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.style.removeProperty("color-scheme");
});

describe("ThemeModeProvider", () => {
  it("persists an explicit dark choice and synchronizes the legacy Tailwind selector", async () => {
    const user = userEvent.setup();
    render(
      <ThemeModeProvider>
        <ThemeProbe />
      </ThemeModeProvider>,
    );

    await user.click(screen.getByRole("button", { name: /use dark theme/i }));

    expect(screen.getByText("dark:dark")).toBeInTheDocument();
    expect(document.documentElement).toHaveClass("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("presidio-color-scheme")).toBe("dark");
  });
});
