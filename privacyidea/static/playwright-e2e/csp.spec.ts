/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import { Locator, Page, Response, test as visitorTest } from "@playwright/test";
import { expect, test } from "./support/test";
import { selfTest, SELF_PASS, SELF_USER } from "./support/self-service";
import { expectAdminPage, expectPath, setSticky, waitForData } from "./support/helpers";
import { ALL_PAGES, SELF_PAGES } from "./support/routes";

// With PI_ENABLE_CSP = True, the server sends a Content Security Policy. It allows inline styles only with the nonce of
// the response, and no inline script at all. Angular puts the nonce on the styles that it adds while it runs, and the
// build of the WebUI writes no inline style or script. The browser blocks every other inline style and script and
// reports it with a securitypolicyviolation event. Each test loads one page, or opens one overlay on it, and fails on
// any such event.
//
// Set E2E_CSP when the instance runs with PI_ENABLE_CSP = True. Without it, the spec skips: without the policy, the
// browser blocks nothing and the tests prove nothing. With E2E_CSP, the self-service user is required as well, so that
// a run cannot skip the self-service pages unnoticed.
const CSP_ENABLED = !!process.env["E2E_CSP"];
const NOT_ENABLED = "E2E_CSP is not set: the instance does not run with PI_ENABLE_CSP = True";

interface ViolationLog {
  cspViolations?: string[];
}

// Records the violations of the page from its start: an init script runs before the first script of the page, and the
// event also reports what the browser blocks while it parses the HTML. Each entry names the directive, what it blocked
// ("inline" for an inline style or script) and the place in the code that tried to add it.
async function recordViolations(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const violations: string[] = [];
    (window as ViolationLog).cspViolations = violations;
    document.addEventListener("securitypolicyviolation", (event) =>
      violations.push(
        `${event.effectiveDirective} blocked ${event.blockedURI} from ${event.sourceFile}:${event.lineNumber}:${event.columnNumber}`
      )
    );
  });
}

// The same violation repeats for each style that one place in the code adds, so the report counts them.
function countViolations(violations: string[]): string[] {
  const counts = new Map<string, number>();
  for (const violation of violations) {
    counts.set(violation, (counts.get(violation) ?? 0) + 1);
  }
  return [...counts].map(([violation, count]) => (count > 1 ? `${violation} (${count} times)` : violation));
}

// Loads `path` with the violation recorder and returns the response, which carries the policy of the page.
async function load(page: Page, path: string): Promise<Response> {
  await recordViolations(page);
  const response = await page.goto(path, { waitUntil: "networkidle" });
  expect(response, `the response to ${path}`).not.toBeNull();
  return response!;
}

// Returns one directive of the policy, for example "style-src 'self' 'nonce-...'", or "" if the policy has none.
function directive(policy: string, name: string): string {
  return (
    policy
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith(`${name} `)) ?? ""
  );
}

// Asserts that the page ran under the expected policy and that the browser blocked nothing on it.
async function expectNothingBlocked(page: Page, response: Response): Promise<void> {
  const policy = response.headers()["content-security-policy"] ?? "";
  // Without a nonce in style-src, the check of the violations below proves nothing.
  expect(directive(policy, "style-src"), "the style-src of the policy").toContain("'nonce-");
  // With a nonce in script-src, anyone who reads the nonce from <app-root> can add an inline script, and a new inline
  // script in the WebUI then passes this check.
  expect(directive(policy, "script-src"), "the script-src of the policy").not.toContain("'nonce-");
  const violations = await page.evaluate(() => (window as ViolationLog).cspViolations ?? null);
  expect(violations, "the violation recorder runs on the page").not.toBeNull();
  // Soft assertions, so that a failure reports what the policy blocked and also what the page lost by it.
  expect
    .soft(countViolations(violations!), "the inline styles and scripts that the Content Security Policy blocked")
    .toEqual([]);
  // A stylesheet that does not apply to the screen leaves the page without its theme and icons. This happens, for
  // example, if a build loads the stylesheet for print first and the policy blocks the script that switches it.
  const media = await page
    .locator('link[rel="stylesheet"]')
    .evaluateAll((links) => links.map((link) => (link as HTMLLinkElement).media));
  expect
    .soft(
      media.filter((value) => value !== "" && value !== "all"),
      "media of the stylesheets that do not apply to the screen"
    )
    .toEqual([]);
}

visitorTest.describe("Content Security Policy, login page", () => {
  // The login page as a visitor sees it, without a session.
  visitorTest.use({ storageState: { cookies: [], origins: [] } });

  visitorTest("login: the policy blocks nothing", async ({ page }) => {
    visitorTest.skip(!CSP_ENABLED, NOT_ENABLED);
    const response = await load(page, "login");
    await expect(page.locator("#username")).toBeVisible();
    await waitForData(page);
    await expectNothingBlocked(page, response);
  });
});

test.describe("Content Security Policy, admin pages", () => {
  test.beforeEach(() => {
    test.skip(!CSP_ENABLED, NOT_ENABLED);
  });

  for (const route of ALL_PAGES) {
    test(`${route.name}: the policy blocks nothing`, async ({ page }) => {
      const response = await load(page, route.path);
      await expectAdminPage(page);
      await expectPath(page, route.path);
      await waitForData(page);
      await expectNothingBlocked(page, response);
    });
  }
});

interface OverlayCase {
  name: string;
  page: string;
  // Opens the overlay and returns it.
  open: (page: Page) => Promise<Locator>;
}

// Angular adds the styles of a menu, a select list, a tooltip or a dialog only when it opens. The tests only open them:
// nothing is selected, saved or confirmed, and the dialog closes with the page at the end of the test.
const OVERLAYS: OverlayCase[] = [
  {
    // The actions trigger shows when the table header is sticky. The users table needs users, and the CI instance has
    // some.
    name: "actions menu",
    page: "users",
    open: async (page) => {
      await setSticky(page, true);
      await page.locator(".table-actions-trigger").first().click();
      return page.locator(".cdk-overlay-pane .mat-mdc-menu-panel").first();
    }
  },
  {
    name: "select list",
    page: "tokens/enrollment",
    open: async (page) => {
      await page.locator("mat-select").first().click();
      return page.locator(".cdk-overlay-pane [role='listbox']").first();
    }
  },
  {
    name: "tooltip",
    page: "dashboard",
    open: async (page) => {
      await page.getByRole("button", { name: "UI Settings" }).hover();
      return page.locator(".cdk-overlay-container .mat-mdc-tooltip").first();
    }
  },
  {
    // The instance needs a realm. The CI instance has one.
    name: "delete confirmation",
    page: "users/realms",
    open: async (page) => {
      await page.getByRole("button", { name: "Delete realm" }).first().click();
      return page.locator("mat-dialog-container").first();
    }
  }
];

test.describe("Content Security Policy, overlays", () => {
  test.beforeEach(() => {
    test.skip(!CSP_ENABLED, NOT_ENABLED);
  });

  for (const overlay of OVERLAYS) {
    test(`${overlay.name}: the policy blocks nothing`, async ({ page }) => {
      const response = await load(page, overlay.page);
      await expectAdminPage(page);
      await waitForData(page);
      // A missing trigger fails the test instead of skipping it, so that a changed page cannot hide the check.
      await expect(await overlay.open(page)).toBeVisible();
      await expectNothingBlocked(page, response);
    });
  }
});

selfTest.describe("Content Security Policy, self-service pages", () => {
  selfTest.beforeEach(() => {
    selfTest.skip(!CSP_ENABLED, NOT_ENABLED);
    expect(SELF_USER && SELF_PASS, "E2E_SELF_USER and E2E_SELF_PASS are set").toBeTruthy();
  });

  for (const route of SELF_PAGES) {
    selfTest(`${route.name}: the policy blocks nothing`, async ({ page }) => {
      const response = await load(page, route.path);
      await expectPath(page, route.path);
      await waitForData(page);
      await expectNothingBlocked(page, response);
    });
  }
});
