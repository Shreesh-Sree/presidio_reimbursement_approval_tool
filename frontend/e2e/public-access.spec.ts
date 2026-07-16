import { expect, test } from "@playwright/test";

test.describe("public access", () => {
  test("protects workspace routes and presents sign-in only", async ({ page }) => {
    await page.goto("/reports");

    await expect(page).toHaveURL(/\/sign-in/);
    await expect(page.getByRole("heading", { name: /expenses,? clearly approved/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /sign in with your work account/i })).toBeVisible();
    await expect(page.getByText(/sign up|create account/i)).toHaveCount(0);
  });
});
