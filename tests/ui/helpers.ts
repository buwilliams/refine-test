import { expect, type APIRequestContext, type APIResponse, type Page } from "@playwright/test";

export const smokeNamespace = "refine-smoke";
export const testAppPath = `${process.cwd()}/test-app`;

export async function jsonObject(response: APIResponse): Promise<Record<string, unknown>> {
  expect(response.ok(), await response.text()).toBeTruthy();
  const data = await response.json();
  expect(typeof data).toBe("object");
  expect(data).not.toBeNull();
  return data as Record<string, unknown>;
}

export async function ensureAttachedProject(request: APIRequestContext): Promise<void> {
  const status = await jsonObject(await request.get("/api/project/status"));
  expect(status.attached).toBe(true);
  expect(status.client_repo).toBe(testAppPath);
}

export async function ensureSmokeReporter(request: APIRequestContext): Promise<void> {
  const current = await jsonObject(await request.get("/api/reporters"));
  const reporters = Array.isArray(current.reporters) ? current.reporters : [];
  const existing = reporters.find((reporter) => {
    return reporter && typeof reporter === "object" && "name" in reporter
      && (reporter as { name?: unknown }).name === smokeNamespace;
  });
  if (existing) return;

  const created = await request.post("/api/reporters", { data: { name: smokeNamespace } });
  expect(created.ok(), await created.text()).toBeTruthy();
}

export interface GapDraft {
  actual: string;
  target: string;
  priority?: "low" | "medium" | "high";
  reporter?: string;
}

/** Create a disposable Gap through the public API and return its id. */
export async function createGap(request: APIRequestContext, draft: GapDraft): Promise<string> {
  await ensureSmokeReporter(request);
  const response = await request.post("/api/gaps", {
    data: {
      reporter: draft.reporter ?? smokeNamespace,
      actual: draft.actual,
      target: draft.target,
      priority: draft.priority ?? "low",
    },
  });
  const body = await jsonObject(response);
  const gap = (body.gap ?? body) as Record<string, unknown>;
  const id = String(gap.id ?? "");
  expect(id).toBeTruthy();
  return id;
}

export async function deleteGap(request: APIRequestContext, id: string): Promise<void> {
  if (!id) return;
  const response = await request.delete(`/api/gaps/${id}`);
  expect(response.ok(), await response.text()).toBeTruthy();
}

/** Select the smoke reporter in the browser before loading the app shell. */
export async function withSmokeReporter(page: Page): Promise<void> {
  await page.addInitScript((name) => {
    window.localStorage.setItem("refine_last_reporter", name);
  }, smokeNamespace);
}
