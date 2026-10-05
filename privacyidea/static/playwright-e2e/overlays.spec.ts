import { expect, Locator, Page } from "@playwright/test";
import { test } from "./support/test";
import { openPage, setSticky } from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";

// Menus and dialogs sit in the overlay layer, outside the page's own tree, and are where focus handling goes wrong:
// the first item must take focus, Escape must close and give focus back, and a dialog must trap it.

interface MenuCase {
  name: string;
  page: string;
  trigger: (page: Page) => Locator;
  prepare?: (page: Page) => Promise<void>;
}

const MENUS: MenuCase[] = [
  { name: "language switcher", page: "dashboard", trigger: (p) => p.locator("app-language-switcher button").first() },
  { name: "theme switcher", page: "dashboard", trigger: (p) => p.locator("app-theme-switcher button").first() },
  { name: "token more filter", page: "tokens", trigger: (p) => p.getByRole("button", { name: "More Filter" }) },
  { name: "container more filter", page: "containers", trigger: (p) => p.getByRole("button", { name: "More Filter" }) },
  {
    name: "token actions",
    page: "tokens",
    trigger: (p) => p.locator(".table-actions-trigger").first(),
    prepare: (p) => setSticky(p, true)
  },
  {
    name: "policy scope filter",
    page: "policies",
    trigger: (p) => p.locator("app-multi-select-filter button").first()
  }
];

for (const scheme of ["light", "dark"] as const) {
  test.describe(`menus, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const menu of MENUS) {
      test(`${menu.name}: opens from the keyboard, names its items and gives focus back on Escape`, async ({
        page
      }, testInfo) => {
        await openPage(page, menu.page);
        await menu.prepare?.(page);
        const trigger = menu.trigger(page);
        test.skip(
          (await trigger.count()) === 0 || !(await trigger.isVisible()),
          "trigger not available on this instance"
        );

        await trigger.focus();
        await page.keyboard.press("Enter");
        const panel = page.locator(".cdk-overlay-pane [role='menu'], .cdk-overlay-pane .mat-mdc-menu-content").first();
        await expect(panel).toBeVisible();

        // A menu opened from the keyboard hands focus to its first item.
        const focusInside = await page.evaluate(() => !!document.activeElement?.closest(".cdk-overlay-container"));
        expect(focusInside, "focus moves into the open menu").toBe(true);

        const unnamed = await page.evaluate(() =>
          [
            ...document.querySelectorAll<HTMLElement>(
              ".cdk-overlay-container [role='menuitem'], .cdk-overlay-container [role='menuitemcheckbox'], .cdk-overlay-container [role='menuitemradio']"
            )
          ]
            .filter((e) => !(e.textContent ?? "").trim() && !e.getAttribute("aria-label"))
            .map((e) => e.className)
        );
        expect(unnamed).toEqual([]);

        await expectNoNewViolations(page, `${menu.name} (menu)`, scheme, testInfo, {
          include: ".cdk-overlay-container"
        });

        await page.keyboard.press("Escape");
        await expect(panel).toBeHidden();
        await expect(trigger).toBeFocused();
      });
    }
  });
}

interface DialogCase {
  name: string;
  page: string;
  open: (page: Page) => Promise<boolean>;
}

// Each opens a confirmation first and is closed with Cancel or Escape; nothing is confirmed, so nothing is deleted.
async function selectFirstRowAndClick(page: Page, label: RegExp): Promise<boolean> {
  const checkbox = page.locator("tr.mat-mdc-row mat-checkbox input").first();
  if ((await checkbox.count()) === 0) {
    return false;
  }
  await checkbox.check({ force: true });
  const button = page.locator(".actions-row").getByRole("button", { name: label }).first();
  if ((await button.count()) === 0 || !(await button.isEnabled())) {
    return false;
  }
  await button.click();
  return true;
}

const DIALOGS: DialogCase[] = [
  { name: "delete tokens", page: "tokens", open: (p) => selectFirstRowAndClick(p, /delete/i) },
  { name: "delete containers", page: "containers", open: (p) => selectFirstRowAndClick(p, /delete/i) },
  { name: "delete policies", page: "policies", open: (p) => selectFirstRowAndClick(p, /delete/i) }
];

for (const scheme of ["light", "dark"] as const) {
  test.describe(`dialogs, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const dialog of DIALOGS) {
      test(`${dialog.name}: has a name, traps focus, closes on Escape`, async ({ page }, testInfo) => {
        await openPage(page, dialog.page);
        test.skip(!(await dialog.open(page)), "nothing to select or the action is not available");

        const box = page.locator("[role='dialog'], [role='alertdialog'], mat-dialog-container").first();
        await expect(box).toBeVisible();

        const named = await box.evaluate(
          (el) => !!(el.getAttribute("aria-label") || el.getAttribute("aria-labelledby"))
        );
        expect(named, "the dialog has an accessible name").toBe(true);

        // Focus starts inside and Tab never leaves.
        expect(
          await page.evaluate(
            () => !!document.activeElement?.closest("[role='dialog'], [role='alertdialog'], mat-dialog-container")
          )
        ).toBe(true);
        for (let i = 0; i < 12; i++) {
          await page.keyboard.press("Tab");
          const inside = await page.evaluate(
            () => !!document.activeElement?.closest("[role='dialog'], [role='alertdialog'], mat-dialog-container")
          );
          expect(inside, `Tab ${i + 1} stays in the dialog`).toBe(true);
        }

        await expectNoNewViolations(page, `${dialog.name} (dialog)`, scheme, testInfo, {
          include: ".cdk-overlay-container"
        });

        await page.keyboard.press("Escape");
        await expect(box).toBeHidden();
      });
    }
  });
}
