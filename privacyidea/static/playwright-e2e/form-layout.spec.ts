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

import { expect, Page } from "@playwright/test";
import { test } from "./support/test";
import { SELF_PASS, SELF_USER, selfTest } from "./support/self-service";
import { ALL_PAGES, SCREEN, SELF_PAGES, ZOOMS } from "./support/routes";
import { DETAIL_PAGES, openFirstRecord } from "./support/records";
import { openPage, settle, settleContent } from "./support/helpers";

// Controls that belong together stay together: a form field in a table cell fills its row like its neighbours, the
// info icon that explains a checkbox stays on the checkbox's row, the label of an outlined field stays inside the
// field, and the controls beside a field sit on the middle of its outline. Nothing is saved: a resolver type is
// chosen, a stage and an action are added to a policy that is then left, the copy dialog of a policy is closed with
// Escape, and expansion panels are opened.

// The resolver types whose form starts with a filled attribute mapping table.
const MAPPING_RESOLVERS = ["EntraID", "Keycloak"];

// For each form field in a cell of the mapping table: how much of the row's height, less its divider, it leaves free.
async function mappingFieldGaps(page: Page): Promise<{ column: string; gap: number }[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>(".mapping-table td mat-form-field")].map((field) => {
      const cell = field.closest("td")!;
      const divider = parseFloat(getComputedStyle(cell).borderBottomWidth) || 0;
      const column = [...cell.classList].find((c) => c.startsWith("mat-column-"))?.replace("mat-column-", "") ?? "";
      return {
        column,
        gap: cell.getBoundingClientRect().height - divider - field.getBoundingClientRect().height
      };
    })
  );
}

test.describe("attribute mapping table", () => {
  for (const type of MAPPING_RESOLVERS) {
    test(`${type} resolver: every field fills its row`, async ({ page }) => {
      await openPage(page, "users/resolvers/new");
      await page.getByRole("combobox", { name: "Type" }).click();
      await page.getByRole("option", { name: type, exact: true }).click();
      await expect(page.locator(".mapping-table td mat-form-field").first()).toBeVisible();
      await settle(page);

      const gaps = await mappingFieldGaps(page);
      expect(gaps.length, "form fields in the mapping table").toBeGreaterThan(0);
      // A select and an input in the same row end on the same line; half a pixel is rounding.
      const short = gaps.filter(({ gap }) => Math.abs(gap) > 0.5).map(({ column, gap }) => `${column}: ${gap}px`);
      expect([...new Set(short)], "fields that do not fill their row").toEqual([]);
    });
  }
});

test.describe("conditional access action", () => {
  test("the re-trigger checkbox stays beside the action select, and its hint beside it, at every zoom", async ({
    page
  }) => {
    await openPage(page, "policies/conditional-access/new");
    await page.getByRole("button", { name: "Add Stage" }).click();
    const stage = page.locator(".ca-stage-item").first();
    await expect(stage).toBeVisible();
    if ((await stage.locator(".ca-action-item").count()) === 0) {
      await stage.getByRole("button", { name: "Add Action" }).click();
    }
    const action = stage.locator(".ca-action-item").first();
    // A new action starts open; one that does not is opened.
    if (!(await action.evaluate((e) => e.classList.contains("mat-expanded")))) {
      await action.locator("mat-expansion-panel-header").click();
    }
    const checkbox = action.locator("mat-checkbox", { hasText: "Re-trigger" });
    const hint = action.getByRole("button", { name: "About re-triggering" });
    const select = action.locator("mat-form-field").first();
    await expect(checkbox).toBeVisible();
    await expect(hint).toBeVisible();

    for (const zoom of ZOOMS) {
      await page.setViewportSize({
        width: Math.round(SCREEN.width / zoom),
        height: Math.round(SCREEN.height / zoom)
      });
      await settle(page);
      const at = `${Math.round(zoom * 100)}% zoom`;
      const box = (await checkbox.boundingBox())!;
      const icon = (await hint.boundingBox())!;
      const iconMiddle = icon.y + icon.height / 2;
      expect.soft(iconMiddle, `${at}: the hint is level with its checkbox`).toBeGreaterThan(box.y);
      expect.soft(iconMiddle, `${at}: the hint is level with its checkbox`).toBeLessThan(box.y + box.height);
      expect.soft(icon.x - (box.x + box.width), `${at}: the hint follows the label, px apart`).toBeLessThanOrEqual(8);
      expect.soft(icon.x, `${at}: the hint comes after the checkbox`).toBeGreaterThanOrEqual(box.x + box.width - 1);
      const field = (await select.boundingBox())!;
      expect
        .soft(box.y, `${at}: the checkbox sits beside the action select, not below it`)
        .toBeLessThan(field.y + field.height);
    }
  });
});

// Material floats the label of an outlined field 6.75px above the top of its outline (the translateY of
// .mdc-floating-label--float-above). A label that has not floated yet is checked where it goes on focus.
const FLOAT_ABOVE_OUTLINE = 6.75;

// The labels of outlined fields that reach above their field's own box, where a sticky header, a clipping container
// or a scrolling dialog body can cover or cut them off. A field without a label has nothing to float.
async function labelsOutsideTheirField(page: Page, root = "body"): Promise<string[]> {
  return page.evaluate(
    ({ root, floatAbove }) =>
      [...document.querySelectorAll<HTMLElement>(`${root} .mat-form-field-appearance-outline`)].flatMap((field) => {
        const label = field.querySelector<HTMLElement>(".mdc-floating-label");
        const outline = field.querySelector<HTMLElement>(".mat-mdc-text-field-wrapper");
        const box = field.getBoundingClientRect();
        if (!label || !outline || box.height === 0) {
          return [];
        }
        const labelTop = label.classList.contains("mdc-floating-label--float-above")
          ? label.getBoundingClientRect().top
          : outline.getBoundingClientRect().top - floatAbove;
        const above = box.top - labelTop;
        return above > 0.5 ? [`${label.textContent?.trim()}: ${above.toFixed(1)}px above its field`] : [];
      }),
    { root, floatAbove: FLOAT_ABOVE_OUTLINE }
  );
}

test.describe("outlined field labels stay inside their field", () => {
  for (const route of ALL_PAGES) {
    test(route.name, async ({ page }) => {
      await openPage(page, route.path);
      expect(await labelsOutsideTheirField(page)).toEqual([]);
    });
  }

  for (const detail of DETAIL_PAGES) {
    test(detail.name, async ({ page }) => {
      const notOpened = await openFirstRecord(page, detail);
      test.skip(!!notOpened, notOpened);
      expect(await labelsOutsideTheirField(page)).toEqual([]);
    });
  }

  // The dialog opens with the new name's field at the top of its scrolling body.
  test("copy policy dialog", async ({ page }) => {
    await openPage(page, "policies");
    const checkbox = page.locator("tr.mat-mdc-row mat-checkbox input").first();
    test.skip((await checkbox.count()) === 0, "no policy to copy");
    await checkbox.check({ force: true });
    await page.getByRole("button", { name: "Copy" }).first().click();
    const dialog = page.locator("mat-dialog-container");
    await expect(dialog.locator(".mat-form-field-appearance-outline").first()).toBeVisible();
    await settle(page);
    expect(await labelsOutsideTheirField(page, "mat-dialog-container")).toEqual([]);
    await page.keyboard.press("Escape");
  });
});

selfTest.describe("self-service: outlined field labels stay inside their field", () => {
  selfTest.skip(!SELF_USER || !SELF_PASS, "E2E_SELF_USER and E2E_SELF_PASS are not set");

  for (const route of SELF_PAGES) {
    selfTest(route.name, async ({ page }) => {
      await page.goto(route.path, { waitUntil: "networkidle" });
      await settleContent(page);
      expect(await labelsOutsideTheirField(page)).toEqual([]);
    });
  }
});

// The small controls in the row of a labelled outlined field whose middle is more than 2px off the middle of the
// field's outline: buttons, checkboxes, switches, button toggle groups and the outline of another field. The field
// must be the only labelled field of the row's item that holds it; a control beside a group of stacked fields is not
// beside any one of them. Controls taller than the outline, and those on another line of a wrapped row, are left out.
// 2px is what the hand-set offsets for a hint line leave: they take a step of the spacing scale for its height.
async function controlsOffTheOutline(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const OUTLINE = ".mat-mdc-text-field-wrapper";
    const LABELLED =
      ".mat-form-field-appearance-outline:has(> .mat-mdc-text-field-wrapper:not(.mdc-text-field--no-label))";
    const CONTROLS = `.mat-mdc-button-base, .mdc-checkbox, .mdc-switch, .mat-button-toggle-group, ${OUTLINE}`;
    const shown = (element: Element, rect: DOMRect) =>
      rect.width > 0 && rect.height > 0 && getComputedStyle(element).visibility !== "hidden";
    const isRow = (element: Element) => {
      const style = getComputedStyle(element);
      if (style.display.includes("flex")) {
        return !style.flexDirection.startsWith("column");
      }
      return style.display.includes("grid") && style.gridTemplateColumns.split(" ").length > 1;
    };
    const named = (element: Element) =>
      (element.closest("mat-checkbox, mat-slide-toggle, .mat-mdc-form-field, button")?.textContent ?? "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 40);
    const problems: string[] = [];
    for (const field of document.querySelectorAll(LABELLED)) {
      const outlineElement = field.querySelector(OUTLINE)!;
      const outline = outlineElement.getBoundingClientRect();
      if (!shown(outlineElement, outline)) {
        continue;
      }
      const middle = (outline.top + outline.bottom) / 2;
      const label = field.querySelector(".mdc-floating-label")?.textContent?.trim();
      const seen = new Set<Element>();
      let item = field;
      for (let level = 0; level < 3 && item.parentElement; level++, item = item.parentElement) {
        const row = item.parentElement;
        if (!isRow(row)) {
          continue;
        }
        if (item !== field && item.querySelectorAll(LABELLED).length > 1) {
          break;
        }
        for (const neighbour of row.children) {
          if (neighbour === item) {
            continue;
          }
          for (const control of [neighbour, ...neighbour.querySelectorAll(CONTROLS)]) {
            if (!control.matches(CONTROLS) || seen.has(control)) {
              continue;
            }
            seen.add(control);
            // A button inside a field (a suffix, a clear button) belongs to that field.
            if (!control.matches(OUTLINE) && control.closest(".mat-mdc-form-field")) {
              continue;
            }
            const rect = control.getBoundingClientRect();
            const besideOutline = rect.bottom > outline.top && rect.top < outline.bottom;
            if (!shown(control, rect) || rect.height > outline.height + 1 || !besideOutline) {
              continue;
            }
            const offset = (rect.top + rect.bottom) / 2 - middle;
            if (Math.abs(offset) > 2) {
              problems.push(`${label} ~ "${named(control)}": ${offset.toFixed(1)}px`);
            }
          }
        }
      }
    }
    return problems;
  });
}

// Opens every closed expansion panel, so the fields in conditional access stages, token types and the like are
// checked too. Panels can hold panels, so it goes round until no closed panel is left, five rounds at most.
async function openAllPanels(page: Page): Promise<void> {
  for (let round = 0; round < 5; round++) {
    const opened = await page.evaluate(() => {
      const headers = [
        ...document.querySelectorAll<HTMLElement>(
          "mat-expansion-panel:not(.mat-expanded):not([disabled]) > mat-expansion-panel-header"
        )
      ].filter((header) => header.getBoundingClientRect().height > 0);
      headers.forEach((header) => header.click());
      return headers.length;
    });
    await settle(page);
    if (opened === 0) {
      break;
    }
  }
}

test.describe("controls beside an outlined field sit on the middle of its outline", () => {
  for (const route of ALL_PAGES) {
    test(route.name, async ({ page }) => {
      await openPage(page, route.path);
      await openAllPanels(page);
      expect(await controlsOffTheOutline(page)).toEqual([]);
    });
  }

  for (const detail of DETAIL_PAGES) {
    test(detail.name, async ({ page }) => {
      const notOpened = await openFirstRecord(page, detail);
      test.skip(!!notOpened, notOpened);
      await openAllPanels(page);
      expect(await controlsOffTheOutline(page)).toEqual([]);
    });
  }
});
