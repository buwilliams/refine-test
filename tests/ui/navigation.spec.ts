import { expect, test } from "@playwright/test";
import { createGap, deleteGap, ensureAttachedProject, jsonObject, testAppPath } from "./helpers";

// Navigation And Evidence — smoke-test.md 44-51.

test("navigates between the primary sections from the nav", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("navigation").getByRole("link", { name: "Dashboard" })).toBeVisible();

  await page.getByRole("navigation").getByRole("link", { name: "Gaps" }).click();
  await expect(page.getByRole("heading", { name: "Gaps", level: 2 })).toBeVisible();

  await page.getByRole("navigation").getByRole("link", { name: "Changes" }).click();
  await expect(page.getByRole("heading", { name: "Changes", level: 2 })).toBeVisible();

  await page.getByRole("navigation").getByRole("link", { name: "Logs" }).click();
  await expect(page.getByRole("heading", { name: "Logs", level: 2 })).toBeVisible();

  await page.getByRole("navigation").getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
});

test("compares current-node and all-node dashboard scope", async ({ page }) => {
  // 44. Understand current work status. 45. Compare current-node with all-node work.
  await page.goto("/");
  const scope = page.getByRole("group", { name: "Dashboard node scope" });
  await expect(scope).toBeVisible();
  await scope.getByRole("button", { name: "All" }).click();
  await expect(page).toHaveURL(/node=all/);
  await scope.getByRole("button", { name: "Current" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
});

test("searches merged Changes", async ({ page }) => {
  // 51. Search merged Changes.
  await page.goto("/#/changes");
  await expect(page.getByRole("heading", { name: "Changes", level: 2 })).toBeVisible();
  await page.locator("#changes-filter-shell > summary").click();
  const search = page.locator("#changes-q");
  await expect(search).toBeVisible();
  await search.fill("refine-smoke-no-such-change");
  // The search is reflected in the URL-driven filter without a runtime error.
  await expect(page.locator("#changes-clear")).toBeVisible();
});

test("filters project activity logs by severity", async ({ page }) => {
  // 48. View activity logs. 50. Filter logs to find relevant activity.
  await page.goto("/#/logs");
  await expect(page.getByRole("heading", { name: "Logs", level: 2 })).toBeVisible();
  await page.locator("#logs-filter-shell > summary").click();
  await expect(page.locator("#logs-q")).toBeVisible();
  const severity = page.locator("#logs-severity");
  await expect(severity).toBeVisible();
  await severity.selectOption("error");
  await expect(page.locator("#logs-clear")).toBeVisible();
});

test("opens logs scoped to a specific Gap", async ({ page, request }) => {
  // 49. Open logs for a specific Gap.
  await ensureAttachedProject(request);
  const id = await createGap(request, {
    actual: "refine-smoke logs actual",
    target: "refine-smoke logs target",
  });
  try {
    const logs = await jsonObject(await request.get(`/api/gaps/${id}/logs`));
    expect(Array.isArray(logs.logs)).toBe(true);

    await page.goto(`/#/logs?gap_id=${id}`);
    await expect(page.getByRole("heading", { name: "Logs", level: 2 })).toBeVisible();
    await expect(page.locator("#logs-gap-id")).toHaveValue(id);
  } finally {
    await deleteGap(request, id);
  }
});

test("browses, searches, and reads target-application files", async ({ request }) => {
  // 46. Browse and search target-application files. 47. Read a large file.
  await ensureAttachedProject(request);

  const tree = await jsonObject(await request.get("/api/files/tree"));
  expect(tree.root).toBe(testAppPath);
  expect(Array.isArray(tree.entries)).toBe(true);
  const names = (tree.entries as Array<{ name?: string }>).map((entry) => entry.name);
  expect(names).toContain("README.md");

  const search = await jsonObject(await request.get("/api/files/search?q=README"));
  const found = (search.entries as Array<{ path?: string }>).map((entry) => entry.path);
  expect(found).toContain("README.md");

  const read = await jsonObject(await request.get("/api/files/read?path=README.md"));
  expect(read.kind).toBe("text");
  expect(typeof read.content).toBe("string");
  expect((read.content as string).length).toBeGreaterThan(0);
});
