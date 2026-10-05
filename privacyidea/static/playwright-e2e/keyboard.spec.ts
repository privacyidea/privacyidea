import { expect, test } from "./support/test";
import { ALL_PAGES, TABLE_PAGES } from "./support/routes";
import { knownFailure } from "./support/known";
import { hasTable, openPage, setSticky } from "./support/helpers";

// Accessibility that axe cannot judge from a static snapshot: document structure, keyboard operation and focus.

test.describe("document structure", () => {
  for (const route of ALL_PAGES) {
    test(`${route.name}: language, title, a main and a navigation landmark`, async ({ page }) => {
      await openPage(page, route.path);
      expect(await page.locator("html").getAttribute("lang")).toMatch(/^[a-z]{2}/);
      expect((await page.title()).trim()).not.toBe("");
      expect(await page.locator("main, [role='main']").count()).toBeGreaterThan(0);
      expect(await page.locator("nav, [role='navigation']").count()).toBeGreaterThan(0);
    });

    test(`${route.name}: a single main landmark`, async ({ page }) => {
      await openPage(page, route.path);
      expect(await page.locator("main, [role='main']").count()).toBe(1);
    });
  }
});

test.describe("tables are described", () => {
  for (const route of TABLE_PAGES) {
    test(`${route.name}: the table has an accessible name`, async ({ page }) => {
      await openPage(page, route.path);
      test.skip(!(await hasTable(page)), "no table on this instance");
      const unnamed = await page.evaluate(() =>
        [...document.querySelectorAll<HTMLElement>(".table-scroll-region table")]
          .filter(
            (t) => !t.getAttribute("aria-label") && !t.getAttribute("aria-labelledby") && !t.querySelector("caption")
          )
          .map((t) => t.className)
      );
      expect(unnamed).toEqual([]);
    });

    test(`${route.name}: a sortable header says how it is sorted`, async ({ page }) => {
      await openPage(page, route.path);
      const sortable = page.locator("th.mat-sort-header");
      test.skip((await sortable.count()) === 0, "no sortable columns");
      const missing = await sortable.evaluateAll((ths) =>
        ths.filter((t) => !t.getAttribute("aria-sort")).map((t) => t.textContent?.trim())
      );
      expect(missing).toEqual([]);
    });
  }
});

test.describe("keyboard", () => {
  for (const route of ALL_PAGES) {
    test(`${route.name}: Tab moves through the page without losing or trapping focus`, async ({ page }) => {
      knownFailure(test, "tab stops visible", route.name);
      await openPage(page, route.path);
      const seen: string[] = [];
      const problems: string[] = [];

      for (let i = 0; i < 60; i++) {
        await page.keyboard.press("Tab");
        const info = await page.evaluate(() => {
          const e = document.activeElement as HTMLElement | null;
          if (!e || e === document.body) {
            return { id: "body", visible: true };
          }
          const r = e.getBoundingClientRect();
          const style = getComputedStyle(e);
          const path: string[] = [];
          for (let n: HTMLElement | null = e; n && path.length < 3; n = n.parentElement) {
            path.push(
              n.tagName.toLowerCase() +
                (n.id ? "#" + n.id : "") +
                (n.className ? "." + String(n.className).split(" ")[0] : "")
            );
          }
          return {
            id: path.join("<"),
            visible: r.width > 0 && r.height > 0 && style.visibility !== "hidden" && style.display !== "none"
          };
        });
        if (info.id === "body" && i > 0) {
          // Focus wrapped to the browser's own UI / the document: the end of the page, not a loss.
          break;
        }
        if (!info.visible) {
          problems.push(`focus on an invisible element: ${info.id}`);
        }
        seen.push(info.id);
      }

      expect(problems).toEqual([]);
      expect(seen.length, "Tab reaches interactive elements").toBeGreaterThan(3);
      // A trap shows as the same few elements again and again.
      expect(new Set(seen).size, "Tab does not cycle inside a few elements").toBeGreaterThan(
        Math.min(seen.length, 8) / 2
      );
    });
  }
});

test.describe("focus indicator", () => {
  // A focused control must look different from the same control unfocused: the control's surroundings are
  // captured focused, focus is taken away, and they are captured again. Identical pixels mean no indicator.
  for (const route of ALL_PAGES) {
    test(`${route.name}: a keyboard-focused control shows a focus indicator`, async ({ page }) => {
      await openPage(page, route.path);
      await page.mouse.move(0, 0);
      const invisible: string[] = [];

      for (let i = 0; i < 20; i++) {
        await page.keyboard.press("Tab");
        const target = await page.evaluate(() => {
          const e = document.activeElement as HTMLElement | null;
          if (!e || e === document.body || !e.matches(":focus-visible")) {
            return null;
          }
          e.scrollIntoView({ block: "nearest", inline: "nearest" });
          const r = e.getBoundingClientRect();
          const name = e.tagName.toLowerCase() + (e.className ? "." + String(e.className).split(" ")[0] : "");
          return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight
            ? { name, x: r.left - 8, y: r.top - 8, width: r.width + 16, height: r.height + 16 }
            : null;
        });
        if (!target) {
          continue;
        }
        const clip = {
          x: Math.max(0, target.x),
          y: Math.max(0, target.y),
          width: Math.min(target.width, 1900),
          height: Math.min(target.height, 400)
        };
        const focused = await page.screenshot({ clip, animations: "disabled" });
        await page.evaluate(() => (document.activeElement as HTMLElement).blur());
        const plain = await page.screenshot({ clip, animations: "disabled" });
        if (focused.equals(plain)) {
          invisible.push(target.name);
        }
        // Back on the same control, as the keyboard would have it.
        await page.keyboard.press("Shift+Tab");
        await page.keyboard.press("Tab");
      }
      expect([...new Set(invisible)]).toEqual([]);
    });
  }
});

test.describe("menus", () => {
  test("tokens: the actions menu opens from the keyboard, closes on Escape and returns focus", async ({ page }) => {
    await openPage(page, "tokens");
    await setSticky(page, true);
    const trigger = page.locator(".table-actions-trigger").first();
    await expect(trigger).toBeVisible();

    await trigger.focus();
    await page.keyboard.press("Enter");
    const menu = page.getByRole("menu").first();
    await expect(menu).toBeVisible();
    // The first item takes focus when a menu opens.
    await expect(menu.getByRole("menuitem").first()).toBeFocused();

    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();
    await expect(trigger).toBeFocused();
  });
});
