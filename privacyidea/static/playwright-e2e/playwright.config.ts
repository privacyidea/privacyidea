import { defineConfig } from "@playwright/test";
import * as path from "path";

// Runs against an already running WebUI (default: the local `ng serve`) and a backend it proxies to.
// The suite only reads: it logs in, visits pages, types into filters and opens menus, never saves.
//
//   BASE_URL   default https://localhost:4200/app/v2/
//   E2E_USER   default admin
//   E2E_PASS   default admin
export const BASE_URL = process.env["BASE_URL"] ?? "https://localhost:4200/app/v2/";

export default defineConfig({
  testDir: __dirname,
  testMatch: "**/*.spec.ts",
  outputDir: path.join(__dirname, "test-results"),
  globalSetup: path.join(__dirname, "support", "global-setup.ts"),
  fullyParallel: true,
  forbidOnly: !!process.env["CI"],
  // One retry: a page measured while the dev server is still settling can fail once; a test that needs it is reported as flaky.
  retries: 1,
  reporter: [["list"], ["html", { outputFolder: path.join(__dirname, "playwright-report"), open: "never" }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
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
