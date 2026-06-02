import { expect, test, type APIRequestContext, type APIResponse } from "@playwright/test";

const smokeNamespace = "refine-smoke";
const testAppPath = `${process.cwd()}/test-app`;


async function jsonObject(response: APIResponse) {
  expect(response.ok(), await response.text()).toBeTruthy();
  const data = await response.json();
  expect(typeof data).toBe("object");
  expect(data).not.toBeNull();
  return data as Record<string, unknown>;
}

async function ensureAttachedProject(request: APIRequestContext) {
  const status = await jsonObject(await request.get("/api/project/status"));
  expect(status.attached).toBe(true);
  expect(status.client_repo).toBe(testAppPath);
}

async function ensureSmokeReporter(request: APIRequestContext) {
  const current = await jsonObject(await request.get("/api/reporters"));
  const reporters = Array.isArray(current.reporters) ? current.reporters : [];
  const existing = reporters.find((reporter) => {
    return reporter && typeof reporter === "object" && "name" in reporter
      && reporter.name === smokeNamespace;
  });
  if (existing) return;

  const created = await request.post("/api/reporters", { data: { name: smokeNamespace } });
  expect(created.ok(), await created.text()).toBeTruthy();
}

test("UI creates and deletes a disposable refine-smoke Gap", async ({ page, request }) => {
  await ensureAttachedProject(request);
  await ensureSmokeReporter(request);

  const suffix = Date.now();
  const actual = `${smokeNamespace} observed UI smoke condition ${suffix}`;
  const target = `${smokeNamespace} expected UI smoke condition ${suffix}`;
  let createdId = "";

  await page.addInitScript((name) => {
    window.localStorage.setItem("refine_last_reporter", name);
  }, smokeNamespace);

  await page.goto("/");

  try {
    await page.getByRole("link", { name: /new gap/i }).click();
    await expect(page.getByRole("dialog", { name: "New Gap" })).toBeVisible();

    await page.locator("textarea[name='actual']").fill(actual);
    await page.locator("textarea[name='target']").fill(target);

    const createResponse = page.waitForResponse((response) => {
      return response.url().includes("/api/gaps") && response.request().method() === "POST";
    });
    await page.getByRole("button", { name: "Create Gap" }).click();
    const response = await createResponse;
    expect(response.ok(), await response.text()).toBeTruthy();
    const created = await response.json();
    createdId = String(created.id || created.gap_id || created.gap?.id || "");
    expect(createdId).toBeTruthy();

    const detail = await jsonObject(await request.get(`/api/gaps/${createdId}`));
    const gap = (detail.gap || detail) as Record<string, unknown>;
    expect(gap.id).toBe(createdId);

    await page.goto(`/#/gaps/${createdId}`);
    await expect(page.getByRole("heading", { name: target })).toBeVisible();
  } finally {
    if (createdId) {
      const deleted = await request.delete(`/api/gaps/${createdId}`);
      expect(deleted.ok(), await deleted.text()).toBeTruthy();
    }
  }
});
