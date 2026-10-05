import { expect, selfTest as test, SELF_PASS, SELF_USER } from "./support/self-service";
import { expectNoNewViolations } from "./support/axe";

// The pages of the self-service user. Needs E2E_SELF_USER / E2E_SELF_PASS (see support/self-service.ts).
const SELF_PAGES = [
  { name: "self tokens", path: "tokens" },
  { name: "self token enrollment", path: "tokens/enrollment" },
  { name: "self assign token", path: "tokens/assign-token" },
  { name: "self containers", path: "containers" },
  { name: "self container create", path: "containers/create" },
  { name: "self user", path: "users" },
  { name: "self audit", path: "logs/audit" },
  { name: "self authentication log", path: "logs/authentication-log" },
  { name: "self news", path: "news" }
];

test.beforeEach(() => {
  test.skip(!SELF_USER || !SELF_PASS, "E2E_SELF_USER and E2E_SELF_PASS are not set");
});

async function open(page: import("@playwright/test").Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "networkidle" });
  await expect(page).not.toHaveURL(/\/login/);
  await page.waitForTimeout(500);
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`self-service, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of SELF_PAGES) {
      test(`${route.name}: axe`, async ({ page }, testInfo) => {
        await open(page, route.path);
        await expectNoNewViolations(page, route.name, scheme, testInfo);
      });
    }
  });
}

test.describe("self-service, structure and layout", () => {
  for (const route of SELF_PAGES) {
    test(`${route.name}: landmarks, title and no sideways page scroll`, async ({ page }) => {
      await open(page, route.path);
      expect(await page.locator("main, [role='main']").count()).toBe(1);
      expect((await page.title()).trim()).not.toBe("");
      expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(
        1
      );
    });
  }
});
