import { expect, test } from "@playwright/test";
import { ensureAttachedProject } from "./helpers";

// Guided Setup — smoke-test.md 20-22.

async function openGuide(page: import("@playwright/test").Page): Promise<void> {
  await page.goto("/");
  // The Guide link lives in the nav context menu; open it, then open the Guide.
  await page.locator("summary.nav-context-summary").click();
  await page.locator("#nav-guide-open").click();
  await expect(page.locator("#guide-panel")).toBeVisible();
}

test("opens the Get Started checklist for the attached app", async ({ page, request }) => {
  // 20. Complete the Get Started checklist for a newly attached app.
  await ensureAttachedProject(request);
  await openGuide(page);
  await expect(page.getByRole("button", { name: "Close Guide" })).toBeVisible();
  await expect(page.locator('[data-guide-category="get-started"]')).toBeVisible();
});

test("searches the Guide reference for field-level help", async ({ page, request }) => {
  // 21. Find field-level setup help in the Guide reference.
  await ensureAttachedProject(request);
  await openGuide(page);
  const search = page.locator("[data-guide-reference-search]");
  await expect(search).toBeVisible();
  await search.fill("start command");
  await expect(search).toHaveValue("start command");
});
