import { expect, test } from "@playwright/test";
import { ensureAttachedProject, jsonObject } from "./helpers";

// Runtime Control — smoke-test.md 62-66 (UI/API surfaces).

test("configures runtime limits for agents", async ({ page, request }) => {
  // 62. Configure runtime limits for agents.
  await ensureAttachedProject(request);
  await page.goto("/#/node/runtime");
  await expect(page.locator("#s-cap")).toBeVisible();

  const before = await jsonObject(await request.get("/api/settings"));
  const original = (before.settings as Record<string, unknown>).parallel_run_cap ?? 5;

  const patched = await request.patch("/api/settings", { data: { parallel_run_cap: 9 } });
  expect(patched.ok(), await patched.text()).toBeTruthy();
  const after = await jsonObject(await request.get("/api/settings"));
  // Settings are persisted as strings; compare numerically.
  expect(Number((after.settings as Record<string, unknown>).parallel_run_cap)).toBe(9);

  await request.patch("/api/settings", { data: { parallel_run_cap: original } });
});

test("pauses and unpauses agent scheduling", async ({ request }) => {
  // 63. Pause and unpause agent scheduling.
  await ensureAttachedProject(request);
  try {
    const paused = await jsonObject(await request.post("/api/processes/agents", { data: { paused: true } }));
    expect(paused.agents_paused).toBe(true);
    const status = await jsonObject(await request.get("/api/processes"));
    expect(status.agents_paused).toBe(true);
  } finally {
    const resumed = await jsonObject(await request.post("/api/processes/agents", { data: { paused: false } }));
    expect(resumed.agents_paused).toBe(false);
  }
});

test("inspects runner processes and background jobs", async ({ page, request }) => {
  // 64 + 65. Stop a stale process / inspect runner processes and background jobs.
  await ensureAttachedProject(request);
  const processes = await jsonObject(await request.get("/api/processes"));
  expect(processes.backend).toBeTruthy();
  expect(Array.isArray(processes.running)).toBe(true);

  await page.goto("/#/system/processes");
  await expect(page.locator(".managed-process-table")).toBeVisible();
  await expect(page.locator("[data-toggle-agent-processes]").first()).toBeVisible();
});

test("views runtime performance metrics", async ({ page, request }) => {
  // 66. View and filter runtime performance metrics.
  await ensureAttachedProject(request);
  await page.goto("/#/system/performance");
  await expect(page.locator("#performance-refresh")).toBeVisible();

  const metrics = await jsonObject(await request.get("/api/performance"));
  expect(Array.isArray(metrics.summary)).toBe(true);
});
