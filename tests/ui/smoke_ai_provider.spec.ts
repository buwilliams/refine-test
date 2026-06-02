import { expect, test } from "@playwright/test";

test("UI browser context uses smoke-ai provider configuration", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("banner")).toBeVisible();
  const settings = await page.request.get("/api/settings");
  expect(settings.ok(), await settings.text()).toBeTruthy();
  const data = await settings.json();
  expect(data.settings.agent_cli).toBe("smoke-ai");
});
