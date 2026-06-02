import { expect, test } from "@playwright/test";

// Support — smoke-test.md 76.

test("offers a way to report a Refine bug or feature request", async ({ page }) => {
  // 76. Report a Refine bug or feature request.
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Request refine feature or bugfix" })).toBeVisible();
});
