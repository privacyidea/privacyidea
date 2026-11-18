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

import { Page, Response, test as visitorTest } from "@playwright/test";
import { expect, test } from "./support/test";
import { selfTest, SELF_PASS, SELF_USER } from "./support/self-service";
import { expectAdminPage, waitForData } from "./support/helpers";
import { ALL_PAGES, SELF_PAGES } from "./support/routes";

// With PI_ENABLE_CSP = True, the server sends a Content Security Policy that allows inline styles and scripts only with
// the nonce of the response. The WebUI must put that nonce on the inline style and script of its index.html and on the
// styles that Angular adds while it runs. The browser blocks every other inline style and script and reports it with a
// securitypolicyviolation event. Each test loads one page and fails on any such event.
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

// Asserts that the browser ended on `path` and not on a page that the app redirected to.
async function expectPath(page: Page, path: string): Promise<void> {
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page).toHaveURL(new RegExp(`/${path.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/?$`));
}

// Asserts that the page ran under a policy with a nonce and that the browser blocked nothing on it.
async function expectNothingBlocked(page: Page, response: Response): Promise<void> {
  const policy = response.headers()["content-security-policy"] ?? "";
  // Without a nonce in the policy, the check of the violations below proves nothing.
  for (const directive of ["script-src", "style-src"]) {
    expect(policy, `the ${directive} of the policy has a nonce`).toMatch(
      new RegExp(`(^|;)\\s*${directive}\\s[^;]*'nonce-`)
    );
  }
  const violations = await page.evaluate(() => (window as ViolationLog).cspViolations ?? null);
  expect(violations, "the violation recorder runs on the page").not.toBeNull();
  // Soft assertions, so that a failure reports what the policy blocked and also what the page lost by it.
  expect
    .soft(countViolations(violations!), "the inline styles and scripts that the Content Security Policy blocked")
    .toEqual([]);
  // The global stylesheet loads for print first, and a script with the nonce switches it to all media. If the policy
  // blocks that script, the page has no theme and no icons.
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
