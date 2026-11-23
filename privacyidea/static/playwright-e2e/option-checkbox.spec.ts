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
import { openPage } from "./support/helpers";

// A multi-select option carries a pseudo-checkbox. The hovered and the keyboard-active row turn opaque primary, and the box
// has to move with the label to on-primary (white in the light theme): a box left in its on-surface colour sinks into the blue.

interface BoxColours {
  label: string;
  frame: string;
  fill: string;
  mark: string;
}

const boxColours = (option: Locator): Promise<BoxColours> =>
  option.evaluate((element) => {
    const box = element.querySelector(".mat-pseudo-checkbox") as HTMLElement;
    const label = element.querySelector(".mdc-list-item__primary-text") as HTMLElement;
    const style = getComputedStyle(box);
    return {
      label: getComputedStyle(label).color,
      frame: style.borderTopColor,
      fill: style.backgroundColor,
      mark: getComputedStyle(box, "::after").borderLeftColor
    };
  });

// The Select Realms select of the policy form's user conditions is a multi-select every instance shows; the realms
// are its options. Nothing is saved: the page is left with the selection discarded.
async function openRealms(page: Page): Promise<Locator> {
  await openPage(page, "policies/new");
  await page.getByRole("tab", { name: "Conditions" }).click();
  await page.getByRole("combobox", { name: "Select Realms" }).click();
  await expect(page.locator(".mat-mdc-select-panel")).toBeVisible();
  const option = page.locator("mat-option").first();
  test.skip((await option.count()) === 0, "the instance has no realm to offer");
  return option;
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`multi-select option checkbox, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    test("the box of a hovered row takes the colour of its label, checked or not", async ({ page }) => {
      const option = await openRealms(page);

      await option.hover();
      await expect
        .poll(async () => {
          const { frame, label } = await boxColours(option);
          return frame === label;
        })
        .toBe(true);

      // Left of the row: the right of it holds the Only button, which would select just this item.
      await option.click({ position: { x: 20, y: 20 } });
      await expect(option).toHaveAttribute("aria-selected", "true");
      await expect
        .poll(async () => {
          const { fill, label } = await boxColours(option);
          return fill === label;
        })
        .toBe(true);
      // The tick is cut out of the white fill in the colour of the row.
      const { fill, mark } = await boxColours(option);
      expect(mark).not.toBe(fill);
    });
  });
}
