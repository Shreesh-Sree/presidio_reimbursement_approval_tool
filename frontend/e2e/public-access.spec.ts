import { expect, test } from "@playwright/test";

test.describe("public access", () => {
  test("protects workspace routes and presents sign-in only", async ({ page }) => {
    await page.goto("/reports");

    await expect(page).toHaveURL(/\/sign-in/);
    await expect(page.getByRole("heading", { name: "AlgoQX" })).toBeVisible();
    await expect(page.getByText("Expense Management")).toBeVisible();
    await expect(page.getByRole("button", { name: /continue with google/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /request access with email/i })).toBeVisible();
  });
});
