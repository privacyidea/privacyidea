import { defineConfig } from "@playwright/test";
import * as path from "path";
import { BASE_URL } from "./support/env";

// Runs against an already running WebUI (default: the local `ng serve`) and a backend it proxies to.
// The suite only reads: it logs in, visits pages, types into filters and opens menus, never saves.
//
//   BASE_URL   default https://localhost:4200/app/v2/
//   E2E_USER   default admin
//   E2E_PASS   default admin
// Playwright empties its output directory when a run starts, which would wipe the artifacts of a run in progress next
// to it; each run writes to a directory of its own. The id is an environment variable so that the workers, which load
// this file again, agree with the process that started them.
process.env["E2E_RUN_ID"] ??= String(process.pid);

export default defineConfig({
  testDir: __dirname,
  testMatch: "**/*.spec.ts",
  outputDir: path.join(__dirname, "test-results", process.env["E2E_RUN_ID"]),
  globalSetup: path.join(__dirname, "support", "global-setup.ts"),
  fullyParallel: true,
  // The pages are independent, so they run side by side; E2E_WORKERS tunes it to the machine.
  workers: Number(process.env["E2E_WORKERS"] ?? 8),
  forbidOnly: !!process.env["CI"],
  // One retry: a page measured while the dev server is still settling can fail once; a test that needs it is reported as flaky.
  retries: 1,
  reporter: [
    ["list"],
    ["html", { outputFolder: path.join(__dirname, "playwright-report", process.env["E2E_RUN_ID"]), open: "never" }]
  ],
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: BASE_URL,
    ignoreHTTPSErrors: true,
    storageState: path.join(__dirname, ".auth", "admin.json"),
    // Animations (menu, collapse, shadow transitions) make measurements race; the app honours this.
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  projects: [{ name: "chromium", use: { browserName: "chromium", viewport: { width: 1920, height: 1080 } } }]
});
