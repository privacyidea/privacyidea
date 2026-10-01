import { chromium, FullConfig } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

// Logs in once and stores the session, so every spec starts authenticated.
export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0].use.baseURL as string;
  const file = path.join(__dirname, "..", ".auth", "admin.json");
  fs.mkdirSync(path.dirname(file), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL, ignoreHTTPSErrors: true });
  const page = await context.newPage();
  await page.goto("login");
  await page.fill("#username", process.env["E2E_USER"] ?? "admin");
  await page.fill("#password", process.env["E2E_PASS"] ?? "admin");
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|tokens)/, { timeout: 20_000 });
  await context.storageState({ path: file });
  // The session lives in sessionStorage, which storageState does not save; support/test.ts restores it.
  const session = await page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage))));
  fs.writeFileSync(path.join(path.dirname(file), "session.json"), session);
  await browser.close();
}
