import { spawnSync } from "node:child_process";

export default async function globalSetup() {
  const result = spawnSync("uv", ["run", "python", "-m", "tests.support.infrastructure", "setup"], {
    cwd: process.cwd(),
    encoding: "utf-8",
    env: process.env
  });
  if (result.status !== 0) {
    throw new Error(`refine-test setup failed\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}`);
  }
}
