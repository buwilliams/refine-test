import { expect, test } from "@playwright/test";
import {
  createGap,
  deleteGap,
  ensureAttachedProject,
  ensureSmokeReporter,
  jsonObject,
  smokeNamespace,
  withSmokeReporter,
} from "./helpers";

// Work Intake — smoke-test.md 23-28.

test("selects the reporter for new work", async ({ page, request }) => {
  // 23. Select the reporter for new work.
  await ensureSmokeReporter(request);
  await withSmokeReporter(page);
  await page.goto("/");
  // The reporter selector lives in the nav context menu; assert it is wired up
  // and offers the smoke reporter without depending on the menu's open state.
  const selector = page.locator("#global-reporter");
  await expect(selector).toHaveCount(1);
  await expect(selector.getByRole("option", { name: smokeNamespace })).toHaveCount(1);
  await expect(selector).toHaveValue(smokeNamespace);
});

test("manages reporters without losing historical attribution", async ({ request }) => {
  // 24. Manage reporters without losing historical Gap attribution.
  await ensureAttachedProject(request);
  const original = `${smokeNamespace}-rep-${Date.now()}`;
  const renamed = `${original}-renamed`;

  const created = await jsonObject(await request.post("/api/reporters", { data: { name: original } }));
  const reporter = (created.reporter ?? created) as Record<string, unknown>;
  const reporterId = String(reporter.id ?? "");
  expect(reporterId).toBeTruthy();

  // A Gap attributed to the reporter must keep its attribution across a rename.
  const gapId = await createGap(request, {
    actual: "attribution actual",
    target: "attribution target",
    reporter: original,
  });

  try {
    const patched = await request.patch(`/api/reporters/${reporterId}`, { data: { name: renamed } });
    expect(patched.ok(), await patched.text()).toBeTruthy();

    const detail = await jsonObject(await request.get(`/api/gaps/${gapId}`));
    const gap = (detail.gap ?? detail) as Record<string, unknown>;
    const rounds = (gap.rounds ?? []) as Array<{ reporter?: string }>;
    expect(rounds[0]?.reporter).toBe(renamed);
  } finally {
    await deleteGap(request, gapId);
    await request.delete(`/api/reporters/${reporterId}`);
  }
});

test("imports multiple Gaps from pasted CSV", async ({ request }) => {
  // 25. Import multiple Gaps from pasted feedback or CSV.
  await ensureSmokeReporter(request);
  const csv = [
    "actual,target,reporter,priority",
    `Login broken,Login works,${smokeNamespace},low`,
    `Slow page,Fast page,${smokeNamespace},medium`,
  ].join("\n");

  const parsed = await jsonObject(await request.post("/api/import/csv/parse", { data: { text: csv } }));
  const drafts = (parsed.drafts ?? []) as Array<Record<string, unknown>>;
  expect(drafts).toHaveLength(2);
  expect(drafts[0].actual).toBe("Login broken");
  expect(drafts[1].priority).toBe("medium");
});

test("finds Gaps by text and status filters", async ({ page, request }) => {
  // 26. Find relevant Gaps by status, reporter, node, text, or activity metadata.
  await ensureAttachedProject(request);
  const marker = `refine-smoke-find-${Date.now()}`;
  const id = await createGap(request, { actual: `${marker} actual`, target: `${marker} target` });

  try {
    await page.goto(`/#/gaps?status=backlog&q=${encodeURIComponent(marker)}`);
    await expect(page.getByRole("heading", { name: "Gaps", level: 2 })).toBeVisible();
    await expect(page.locator(`tr[data-id="${id}"]`)).toBeVisible();

    await page.goto(`/#/gaps?q=${encodeURIComponent(marker)}-absent`);
    await expect(page.locator(`tr[data-id="${id}"]`)).toHaveCount(0);
  } finally {
    await deleteGap(request, id);
  }
});

test("exposes bulk-edit controls on the Gaps list", async ({ page }) => {
  // 27. Bulk-edit selected Gaps from the Gaps list.
  await page.goto("/#/gaps");
  await expect(page.getByRole("heading", { name: "Gaps", level: 2 })).toBeVisible();
  await page.locator("#gaps-filter-shell > summary").click();
  await expect(page.locator("#bulk-set-status")).toBeVisible();
  await expect(page.locator("#bulk-set-priority")).toBeVisible();
  await expect(page.locator("#bulk-set-reporter")).toBeVisible();
  await expect(page.locator("#bulk-delete")).toBeVisible();
});
