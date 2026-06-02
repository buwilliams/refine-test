import { expect, test } from "@playwright/test";
import { ensureAttachedProject, jsonObject, testAppPath } from "./helpers";

// Application Lifecycle — smoke-test.md 12, 14, 15, 17, 18.

test("lists attached applications and exposes lifecycle controls", async ({ page, request }) => {
  // 12. Create a new application. 14. Swap apps. 15. Remove the current application.
  await ensureAttachedProject(request);

  const projects = await jsonObject(await request.get("/api/projects"));
  const apps = (projects.apps ?? []) as Array<{ path?: string }>;
  expect(apps.some((app) => app.path === testAppPath)).toBe(true);

  await page.goto("/#/project/application");
  await expect(page.locator("#s-project-select")).toBeVisible();
  await expect(page.locator("#s-project-add")).toBeVisible();
  await expect(page.locator("#s-project-switch")).toBeVisible();
  await expect(page.locator("#s-project-remove")).toBeVisible();
});

test("generates target-application commands with AI", async ({ request }) => {
  // 17. Generate target-application commands with AI (deterministic smoke-ai).
  await ensureAttachedProject(request);
  const generated = await jsonObject(
    await request.post("/api/target-app/generate-instructions", { data: { action: "start" } }),
  );
  expect(generated.ok).toBe(true);
  expect(generated.config).toBeTruthy();
});

test("reports target-application health", async ({ request }) => {
  // 18. Confirm the target application reports healthy (status surface).
  await ensureAttachedProject(request);
  const health = await jsonObject(await request.post("/api/target-app/health", { data: {} }));
  // The disposable app has no run commands configured; the health surface still
  // reports a structured state rather than erroring.
  expect(typeof health.state).toBe("string");
  expect("last_check_ok" in health).toBe(true);
});
