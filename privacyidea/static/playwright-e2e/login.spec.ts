import { expect, test } from "@playwright/test";
import { expectNoNewViolations } from "./support/axe";

// The login page, as a visitor sees it: no session, so these tests use the plain Playwright test rather than the one
// in support/test.ts that restores the administrator's.
test.use({ storageState: { cookies: [], origins: [] } });

for (const scheme of ["light", "dark"] as const) {
  test.describe(`login, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    test("axe finds nothing beyond the baseline", async ({ page }, testInfo) => {
      await page.goto("login", { waitUntil: "networkidle" });
      await expect(page.locator("#username")).toBeVisible();
      await expectNoNewViolations(page, "login", scheme, testInfo);
    });
  });
}

test.describe("login", () => {
  test("the page is named by a heading the visitor does not see", async ({ page }) => {
    await page.goto("login", { waitUntil: "networkidle" });
    await expect(page.locator("#username")).toBeVisible();

    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toHaveCount(1);
    await expect(h1).toHaveText("Login");
    // It is read, not drawn: a clipped 1px box, so it takes no room above the form.
    const box = await h1.boundingBox();
    expect(box?.width).toBeLessThanOrEqual(2);
    expect(box?.height).toBeLessThanOrEqual(2);
    expect(await page.title()).toMatch(/^Login – /);
  });

  test("the form starts on the username, and Tab reaches the password, its toggle and the passkey button", async ({
    page
  }) => {
    await page.goto("login", { waitUntil: "networkidle" });
    await expect(page.locator("#username")).toBeFocused();

    const reached: string[] = [];
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press("Tab");
      reached.push(
        await page.evaluate(() => {
          const e = document.activeElement as HTMLElement;
          return e.id || e.getAttribute("aria-label") || e.tagName.toLowerCase();
        })
      );
    }
    // The submit button is disabled until the form is filled in, so Tab passes it.
    expect(reached[0]).toBe("password");
    expect(reached[1]).toMatch(/password/i);
    expect(reached[2]).toMatch(/passkey/i);
  });
});
