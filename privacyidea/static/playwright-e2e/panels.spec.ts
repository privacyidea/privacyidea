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

import { expect, Locator, Page } from "@playwright/test";
import { test } from "./support/test";
import { openPage, settle } from "./support/helpers";

// The expansion panels: a header is one height open or closed, its chevron stands out on the hovered header, and the
// panel of the actions a policy can take says how many there are. Nothing is saved: panels are opened and closed and
// a filter is typed.

// The resolver form shows its panels once a type is chosen; an EntraID resolver has one that starts closed.
async function openResolverPanels(page: Page): Promise<Locator> {
  await openPage(page, "users/resolvers/new");
  await page.getByRole("combobox", { name: "Type" }).click();
  await page.getByRole("option", { name: "EntraID" }).click();
  const panels = page.locator(".mat-expansion-panel");
  await expect(panels.first()).toBeVisible();
  // By position, so the locator keeps naming this panel once it is open.
  const closed = await panels.evaluateAll((all) => all.findIndex((panel) => !panel.classList.contains("mat-expanded")));
  expect(closed, "a panel that starts closed").toBeGreaterThanOrEqual(0);
  return panels.nth(closed).locator("> .mat-expansion-panel-header");
}

const height = async (locator: Locator) => Math.round((await locator.boundingBox())!.height);

// The colours the page paints at two points, read from a screenshot: the colours are translucent layers over a
// gradient, which computed styles do not add up.
async function paintedAt(page: Page, points: { x: number; y: number }[]): Promise<number[][]> {
  const shot = (await page.screenshot()).toString("base64");
  return page.evaluate(
    async ({ shot, points }) => {
      const image = await createImageBitmap(await (await fetch(`data:image/png;base64,${shot}`)).blob());
      const canvas = document.createElement("canvas");
      canvas.width = image.width;
      canvas.height = image.height;
      const context = canvas.getContext("2d")!;
      context.drawImage(image, 0, 0);
      const scale = image.width / innerWidth;
      return points.map(({ x, y }) => [
        ...context.getImageData(Math.round(x * scale), Math.round(y * scale), 1, 1).data.slice(0, 3)
      ]);
    },
    { shot, points }
  );
}

const luminance = ([r, g, b]: number[]) => {
  const channel = (value: number) => {
    const v = value / 255;
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
};

test.describe("expansion panels", () => {
  test("a header is as tall closed as it is open, so opening a panel does not move its title", async ({ page }) => {
    const header = await openResolverPanels(page);
    const closed = await height(header);
    const panel = header.locator("xpath=..");
    await header.click();
    await expect(panel).toHaveClass(/mat-expanded/);
    await settle(page);
    expect(await height(panel.locator("> .mat-expansion-panel-header")), "open header height").toBe(closed);
  });

  for (const scheme of ["light", "dark"] as const) {
    test.describe(`${scheme} theme`, () => {
      test.use({ colorScheme: scheme });

      test("the chevron's circle stands out on the hovered header of a closed panel", async ({ page }) => {
        const header = await openResolverPanels(page);
        await header.scrollIntoViewIfNeeded();
        await header.hover();
        const indicator = header.locator(".mat-expansion-indicator");
        // The header and the circle fade in.
        await expect
          .poll(() => indicator.evaluate((e) => getComputedStyle(e).backgroundColor))
          .not.toMatch(/rgba\(0, 0, 0, 0\)|transparent/);
        await page.waitForTimeout(300);

        const circle = (await indicator.boundingBox())!;
        const middle = circle.y + circle.height / 2;
        const [onCircle, beside] = await paintedAt(page, [
          // Inside the circle, left of the glyph in its centre.
          { x: circle.x + 5, y: middle },
          // On the header, left of the circle.
          { x: circle.x - 24, y: middle }
        ]);
        const [high, low] = [luminance(onCircle), luminance(beside)].sort((a, b) => b - a);
        // No criterion names a number for a state layer on a state layer; 1.2:1 is a step the eye picks out, where
        // an 8% layer on a hovered header (1.1:1) is not.
        expect((high + 0.05) / (low + 0.05), "circle against the hovered header").toBeGreaterThanOrEqual(1.2);
      });
    });
  }

  test("without a scope, the panel of the actions to add shows how many it lists", async ({ page }) => {
    await openPage(page, "policies/new");
    const panel = page.locator(".action-selector-container > mat-expansion-panel");
    const total = panel.locator("> mat-expansion-panel-header mat-panel-description");
    const items = panel.locator("app-policy-action-item-new");

    const all = await items.count();
    expect(all, "actions offered without a scope").toBeGreaterThan(0);
    await expect(total).toHaveText(String(all));

    // The number follows the search: it is the count of what the panel lists, not of what exists.
    // The search has a second copy for the pinned header, hidden until the page scrolls.
    await page.locator("app-policy-action-search:not(.hidden) input").fill("pin");
    await expect.poll(() => items.count()).toBeLessThan(all);
    await expect(total).toHaveText(String(await items.count()));
  });
});
