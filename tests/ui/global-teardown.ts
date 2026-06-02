import { spawnSync } from "node:child_process";

export default async function globalTeardown() {
  const result = spawnSync("uv", ["run", "python", "-m", "tests.support.infrastructure", "teardown"], {
    cwd: process.cwd(),
    encoding: "utf-8",
    env: process.env
  });
  if (result.status !== 0) {
    throw new Error(`refine-test teardown failed\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}`);
  }
}
