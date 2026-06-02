import { expect, test } from "@playwright/test";
import {
  createGap,
  deleteGap,
  ensureAttachedProject,
  jsonObject,
  smokeNamespace,
} from "./helpers";

// Gap Management — smoke-test.md 29-35.

test("opens a Gap as a modal without losing the underlying screen", async ({ page, request }) => {
  // 29. Open a Gap without losing the current screen context.
  await ensureAttachedProject(request);
  const target = `refine-smoke detail ${Date.now()}`;
  const id = await createGap(request, { actual: "detail actual", target });
  try {
    await page.goto("/#/gaps");
    await expect(page.getByRole("heading", { name: "Gaps", level: 2 })).toBeVisible();
    await page.goto(`/#/gaps/${id}`);
    const dialog = page.getByRole("dialog", { name: "Gap detail" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: target })).toBeVisible();
    // Dismissing the modal returns to the underlying Gaps list.
    await dialog.getByRole("button", { name: "Close" }).click();
    await expect(page.getByRole("heading", { name: "Gaps", level: 2 })).toBeVisible();
  } finally {
    await deleteGap(request, id);
  }
});

test("revises the latest feedback round", async ({ request }) => {
  // 30. Add a new round of feedback to a Gap (user-driven round revision).
  await ensureAttachedProject(request);
  const id = await createGap(request, { actual: "round actual", target: "round target" });
  // Pause agents so the Gap stays in `todo` (the runner would otherwise pick it
  // up, and a round may only be edited from todo/review/failed).
  await request.post("/api/processes/agents", { data: { paused: true } });
  try {
    const moved = await request.post("/api/gaps/bulk", {
      data: { update: { status: "todo" }, gap_ids: [id] },
    });
    expect(moved.ok(), await moved.text()).toBeTruthy();

    const edited = await request.patch(`/api/gaps/${id}/rounds/latest`, {
      data: { reporter: smokeNamespace, actual: "revised actual", target: "revised target" },
    });
    const body = await jsonObject(edited);
    const gap = (body.gap ?? body) as Record<string, unknown>;
    const rounds = (gap.rounds ?? []) as Array<{ actual?: string }>;
    expect(rounds.at(-1)?.actual).toBe("revised actual");
  } finally {
    await request.post("/api/processes/agents", { data: { paused: false } });
    await deleteGap(request, id);
  }
});

test("changes a Gap's name and priority", async ({ request }) => {
  // 31. Change a Gap's name, priority, or reporter.
  await ensureAttachedProject(request);
  const id = await createGap(request, { actual: "rename actual", target: "rename target" });
  try {
    const patched = await request.patch(`/api/gaps/${id}`, {
      data: { name: "refine-smoke renamed", priority: "high" },
    });
    expect(patched.ok(), await patched.text()).toBeTruthy();

    const detail = await jsonObject(await request.get(`/api/gaps/${id}`));
    const gap = (detail.gap ?? detail) as Record<string, unknown>;
    expect(gap.name).toBe("refine-smoke renamed");
    expect(gap.priority).toBe("high");
  } finally {
    await deleteGap(request, id);
  }
});

test("moves a Gap between user-allowed workflow states", async ({ request }) => {
  // 32. Move a Gap between backlog, todo, ... where user action is allowed.
  await ensureAttachedProject(request);
  const id = await createGap(request, { actual: "move actual", target: "move target" });
  // Pause agent scheduling so the Gap stays in the state we set; otherwise the
  // runner immediately picks up `todo` and advances it (in-progress -> ...).
  await request.post("/api/processes/agents", { data: { paused: true } });
  try {
    const toTodo = await jsonObject(
      await request.post("/api/gaps/bulk", { data: { update: { status: "todo" }, gap_ids: [id] } }),
    );
    expect(toTodo.updated).toBe(1);
    await expect
      .poll(async () => {
        const detail = await jsonObject(await request.get(`/api/gaps/${id}`));
        return (detail.gap as Record<string, unknown>).status;
      })
      .toBe("todo");
  } finally {
    await request.post("/api/processes/agents", { data: { paused: false } });
    await deleteGap(request, id);
  }
});

test("cancels and deletes a Gap", async ({ request }) => {
  // 33. Cancel or delete a Gap.
  await ensureAttachedProject(request);
  const id = await createGap(request, { actual: "cancel actual", target: "cancel target" });
  let deleted = false;
  try {
    const cancelled = await request.post(`/api/gaps/${id}/cancel`);
    expect(cancelled.ok(), await cancelled.text()).toBeTruthy();
    const detail = await jsonObject(await request.get(`/api/gaps/${id}`));
    expect((detail.gap as Record<string, unknown>).status).toBe("cancelled");

    await deleteGap(request, id);
    deleted = true;
    const after = await request.get(`/api/gaps/${id}`);
    expect(after.status()).toBe(404);
  } finally {
    if (!deleted) await deleteGap(request, id);
  }
});

test("opens an agent chat with Gap context", async ({ request }) => {
  // 34. Open chat with the agent using Gap context.
  await ensureAttachedProject(request);
  const id = await createGap(request, { actual: "chat actual", target: "chat target" });
  let sessionId = "";
  try {
    const started = await jsonObject(await request.post("/api/chat/start", { data: { gap_id: id } }));
    sessionId = String(started.session_id ?? "");
    expect(sessionId).toBeTruthy();
  } finally {
    if (sessionId) await request.post(`/api/chat/${sessionId}/stop`);
    await deleteGap(request, id);
  }
});

test("opens the planning chat dock for drafting Gaps", async ({ page, request }) => {
  // 35. Draft Gaps from a planning chat.
  await ensureAttachedProject(request);
  await page.goto("/#/gaps/plan");
  // The planning flow opens the chat dock with a "Plan" tab over the Gaps list.
  const dock = page.locator("#toolbar-dock");
  await expect(dock).toBeVisible();
  await expect(dock.locator('[data-tab-id="plan"]')).toBeVisible();
});
