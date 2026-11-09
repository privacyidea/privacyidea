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

import { Browser, BrowserContext, Page } from "@playwright/test";
import { attachPageOnFailure, expect, newAdminContext, test } from "./support/test";
import { expectTableOrState, openPage, settle, settleContent } from "./support/helpers";
import { ClipProblem, clippedControls } from "./support/clipping";
import { DETAIL_PAGES, openFirstRecord } from "./support/records";
import { SCREEN, TABLE_PAGES, ZOOMS } from "./support/routes";

// #6275: a cell whose text is longer than the cell must not hide its actions. The copy button of a serial, the button
// that edits a user and the inputs next to long names are all clipped or covered when the text takes the room.
// Each page is loaded once and checked at every browser zoom, since a zoomed page has the narrower cells.

async function atEachZoom(page: Page, check: (zoom: number) => Promise<void>): Promise<void> {
  for (const zoom of [...ZOOMS].reverse()) {
    await page.setViewportSize({ width: Math.round(SCREEN.width / zoom), height: Math.round(SCREEN.height / zoom) });
    await settle(page);
    await check(zoom);
  }
  await page.setViewportSize({ width: SCREEN.width, height: SCREEN.height });
  await settle(page);
}

const describe = (problems: ClipProblem[]): string[] => [...new Set(problems.map((p) => `${p.control}: ${p.problem}`))];

async function expectEveryControlReachable(page: Page): Promise<void> {
  await atEachZoom(page, async (zoom) => {
    expect.soft(describe(await clippedControls(page)), `${Math.round(zoom * 100)}% zoom`).toEqual([]);
  });
}

test.describe("table pages: no control is clipped or covered", () => {
  for (const route of TABLE_PAGES) {
    test(route.name, async ({ page }) => {
      await openPage(page, route.path);
      test.skip(!(await expectTableOrState(page)), "the list is empty, the page shows its empty state");
      await expectEveryControlReachable(page);
    });
  }
});

test.describe("detail pages: no control is clipped or covered", () => {
  for (const detail of DETAIL_PAGES) {
    test.describe(detail.name, () => {
      let context: BrowserContext;
      let page: Page;
      let notOpened: string | undefined;

      test.beforeAll(async ({ browser }: { browser: Browser }, testInfo) => {
        context = await newAdminContext(browser, testInfo);
        page = await context.newPage();
        notOpened = await openFirstRecord(page, detail);
      });

      attachPageOnFailure(() => page);

      test.afterAll(async () => {
        await context?.close();
      });

      test("every control stays reachable at each zoom", async () => {
        test.skip(!!notOpened, notOpened);
        await expectEveryControlReachable(page);
      });
    });
  }
});

// A user name far longer than any cell: the edit and unassign buttons of the container's user row must not cover it.
const LONG_USER = "a.very.long.user.name.of.a.person.with.a.long.last.name@example-company-department.example.org";

test.describe("container details with a long user name", () => {
  test("the user row keeps its buttons clear of the name at each zoom", async ({ page }) => {
    await page.route("**/proxy/container/?container_serial=*", async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      const container = body.result.value.containers[0];
      container.users = [{ user_name: LONG_USER, user_realm: "realm1", user_resolver: "resolver1", user_id: "0" }];
      await route.fulfill({ response, json: body });
    });
    await openPage(page, "containers");
    test.skip((await page.locator("tr.mat-mdc-row").count()) === 0, "no container to open");
    await page.locator("tr.mat-mdc-row td.mat-column-serial").locator("a").first().click();
    await page.waitForLoadState("networkidle");
    await settleContent(page);
    await expect(page.getByText(LONG_USER)).toBeVisible();
    await expectEveryControlReachable(page);
  });
});

// The input that picks a user is as wide as its cell when the container details page is narrow, instead of what the save
// and cancel buttons leave of it. Only opens the editor; nothing is saved.
test.describe("container details, choosing a user", () => {
  test("the user input takes the width of its cell at each zoom", async ({ page }) => {
    await page.route("**/proxy/container/?container_serial=*", async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.result.value.containers[0].users = [];
      await route.fulfill({ response, json: body });
    });
    await openPage(page, "containers");
    test.skip((await page.locator("tr.mat-mdc-row").count()) === 0, "no container to open");
    await page.locator("tr.mat-mdc-row td.mat-column-serial").locator("a").first().click();
    await page.waitForLoadState("networkidle");
    await settleContent(page);
    await page.getByRole("button", { name: "Assign User" }).click();
    const field = page.locator("app-container-details-user mat-form-field").filter({ hasText: "Enter User" });
    await expect(field).toBeVisible();
    const realm = page.locator("app-container-details-user mat-form-field").filter({ hasText: "Select Realm of User" });

    await atEachZoom(page, async (zoom) => {
      // The realm select and the user input, one above the other, are the same width.
      const [realmWidth, userWidth] = await Promise.all([
        realm.evaluate((f) => f.getBoundingClientRect().width),
        field.evaluate((f) => f.getBoundingClientRect().width)
      ]);
      expect
        .soft(
          Math.abs(realmWidth - userWidth),
          `${Math.round(zoom * 100)}% zoom: realm ${realmWidth}px, user ${userWidth}px`
        )
        .toBeLessThanOrEqual(1);
      const { input, room } = await field.evaluate((f) => {
        const cell = f.closest("td")!;
        const style = getComputedStyle(cell);
        return {
          input: f.querySelector("input")!.getBoundingClientRect().width,
          room: cell.getBoundingClientRect().width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
        };
      });
      // The field is capped at its own maximum width (--input-width-m), and fills a cell narrower than that. The input
      // is what is left of the field after its padding and the clear button.
      const wanted = Math.min(room, 240) * 0.7;
      expect
        .soft(input, `${Math.round(zoom * 100)}% zoom: the input is ${input}px in ${room}px of room`)
        .toBeGreaterThan(wanted);
    });
  });
});
