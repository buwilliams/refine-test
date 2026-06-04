import { expect, type Locator, type Page, test } from "@playwright/test";
import { ensureAttachedProject } from "./helpers";

// Guided Setup — smoke-test.md 20-22.

async function openGuide(page: Page): Promise<Locator> {
  await page.goto("/");
  // The Guide link lives in the nav context menu; open it, then open the Guide.
  await page.locator("summary.nav-context-summary").click();
  await page.locator("#nav-guide-open").click();
  const guide = page.locator("#guide-panel");
  await expect(guide).toBeVisible();
  return guide;
}

test("opens the Get Started checklist for the attached app", async ({ page, request }) => {
  // 20. Complete the Get Started checklist for a newly attached app.
  await ensureAttachedProject(request);
  const guide = await openGuide(page);
  await expect(guide.getByRole("button", { name: "Close Guide" })).toBeVisible();
  await expect(guide.getByRole("tab", { name: "Get Started" })).toHaveAttribute("aria-selected", "true");
  await expect(guide.getByRole("button", { name: "Add app", exact: true })).toBeVisible();
});

test("searches the Guide reference for field-level help", async ({ page, request }) => {
  // 21. Find field-level setup help in the Guide reference.
  await ensureAttachedProject(request);
  const guide = await openGuide(page);
  await guide.getByRole("tab", { name: "Reference" }).click();
  const search = guide.locator("[data-guide-reference-search]");
  await expect(search).toBeVisible();
  await search.fill("start command");
  await expect(search).toHaveValue("start command");
});
