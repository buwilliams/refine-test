import { expect, test } from "@playwright/test";
import { ensureAttachedProject, jsonObject, withSmokeReporter } from "./helpers";

// Review And Quality — smoke-test.md 36, 39-43.

test("shows the reporter's review queue on the dashboard", async ({ page, request }) => {
  // 36. See all review work assigned to the active reporter.
  await ensureAttachedProject(request);
  await withSmokeReporter(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
  // With a reporter selected, the "Awaiting your review" panel renders.
  await expect(page.locator("#reviews-for-reporter-card")).toBeVisible();
  await expect(page.getByText("Awaiting your review")).toBeVisible();
});

test("configures project Governance context", async ({ page, request }) => {
  // 39 + 41. Review and configure Governance context, constitution, and rules.
  await ensureAttachedProject(request);
  await page.goto("/#/project/governance");
  await expect(page.locator("#governance-rules-list")).toBeVisible();
  await expect(page.locator("#s-governance-generate")).toBeVisible();

  const product = `refine-smoke governance ${Date.now()}`;
  const saved = await jsonObject(
    await request.patch("/api/governance", { data: { product, constitution: "", rules: [] } }),
  );
  expect(saved.product).toBe(product);

  const readback = await jsonObject(await request.get("/api/governance"));
  expect(readback.product).toBe(product);

  // Restore the empty default so the disposable project is left clean.
  await request.patch("/api/governance", { data: { product: "", constitution: "", rules: [] } });
});

test("configures project Quality requirements", async ({ page, request }) => {
  // 40 + 43. Review and configure Quality requirements and instructions.
  await ensureAttachedProject(request);
  await page.goto("/#/project/quality");
  await expect(page.locator("#s-quality-enabled")).toBeVisible();

  const requirement = `refine-smoke quality ${Date.now()}`;
  const saved = await jsonObject(
    await request.patch("/api/quality", { data: { business_requirements: requirement } }),
  );
  expect(saved.business_requirements).toBe(requirement);

  await request.patch("/api/quality", { data: { business_requirements: "" } });
});

test("configures project Guidance", async ({ page, request }) => {
  // 42. Configure project Guidance that applies only to matching Gaps.
  await ensureAttachedProject(request);
  await page.goto("/#/project/guidance");
  await expect(page.locator("#guidance-add")).toBeVisible();

  const guidance = await jsonObject(await request.get("/api/guidance"));
  expect(Array.isArray(guidance.guidance)).toBe(true);
});
