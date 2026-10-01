import { test as base } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

export { expect } from "@playwright/test";

const SESSION_FILE = path.join(__dirname, "..", ".auth", "session.json");

// The WebUI keeps its session in sessionStorage, which a stored browser state does not carry over. This
// restores what global-setup saved after login, before any page script runs.
export const test = base.extend({
  context: async ({ context }, use) => {
    const session = fs.readFileSync(SESSION_FILE, "utf8");
    await context.addInitScript((entries: string) => {
      if (location.origin === "null") {
        return;
      }
      for (const [key, value] of Object.entries(JSON.parse(entries) as Record<string, string>)) {
        if (sessionStorage.getItem(key) === null) {
          sessionStorage.setItem(key, value);
        }
      }
    }, session);
    await use(context);
  }
});
