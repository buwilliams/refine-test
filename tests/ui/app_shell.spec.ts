import { expect, test } from "@playwright/test";

const testAppPath = `${process.cwd()}/test-app`;

test("UI shell renders without browser runtime errors", async ({ page }) => {
  const browserErrors: string[] = [];

  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      browserErrors.push(message.text());
    }
  });

  await page.goto("/");
  const status = await page.request.get("/api/project/status");
  expect(status.ok(), await status.text()).toBeTruthy();
  const project = await status.json();
  expect(project.client_repo).toBe(testAppPath);

  await expect(page).toHaveTitle(/refine/i);
  await expect(page.getByRole("banner")).toBeVisible();
  await expect(page.getByRole("navigation").getByRole("link", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.locator("#active-node-label")).toBeVisible();

  await page.waitForTimeout(500);
  expect(browserErrors).toEqual([]);
});
