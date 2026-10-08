import { Browser, BrowserContext, Locator, Page } from "@playwright/test";
import { expect, newAdminContext, test } from "./support/test";
import { ALL_PAGES, SCREEN, TABLE_PAGES, ZOOMS } from "./support/routes";
import { knownFailure } from "./support/known";
import { focusIndicatorMisses } from "./support/focus";
import { expectTableOrState, hasTable, openPage, resetFocusStart, settle } from "./support/helpers";

// Every page is loaded once and all of its checks run against that one load: structure, the accessibility tree,
// motion, column widths, the keyboard, and last the layout at each browser zoom and at 320 CSS px (it resizes the
// window; the zoom steps go from the widest window to the narrowest, as a user zooming in does). (A page load is by
// far the most expensive step; a test per check used to load each page six times over.)
//
// Browser zoom is emulated the way Chrome applies it on a 1920x1080 screen: the CSS viewport shrinks. The pixel
// ratio would only matter for screenshots, so the viewport is resized rather than the page reloaded at each size.

const sized = (zoom: number) => ({
  width: Math.round(SCREEN.width / zoom),
  height: Math.round(SCREEN.height / zoom)
});

// Controls that must carry a name, and the heading levels, as the accessibility tree lists them.
const NAMED_ROLES =
  "button|link|checkbox|radio|switch|textbox|combobox|slider|menuitem|tab|option|searchbox|spinbutton";
const UNNAMED = new RegExp(`^\\s*- (${NAMED_ROLES})(?: \\[[^\\]]*\\])*:?$`, "gm");
const HEADING = /^\s*- heading "[^"]*" \[level=(\d)\]/gm;

async function sideways(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

// How far anything in the filter row reaches past its card.
async function spill(page: Page): Promise<number> {
  return page.evaluate(() => {
    const row = document.querySelector<HTMLElement>(".filter-paginator-container");
    if (!row) {
      return 0;
    }
    const card = row.getBoundingClientRect();
    return Math.max(
      0,
      // A button's invisible 48px touch target is allowed to overhang its 40px box.
      ...[...row.querySelectorAll<HTMLElement>("*:not(.mat-mdc-button-touch-target)")].map((e) => {
        const r = e.getBoundingClientRect();
        return r.width === 0 ? 0 : Math.max(r.right - card.right, card.left - r.left);
      })
    );
  });
}

const columnWidths = (page: Page) =>
  page.evaluate(() => [...document.querySelectorAll("th")].map((t) => Math.round(t.getBoundingClientRect().width)));

const tierWidths = (page: Page) =>
  page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    // Only the s/m/l/xl tiers have a --column-width-* token.
    return [...document.querySelectorAll<HTMLElement>("th")].flatMap((th) => {
      const tier = /(?:^|\s)col-width-(s|m|l|xl)(?:\s|$)/.exec(th.className)?.[1];
      return tier
        ? [
            {
              label: `${th.textContent?.trim()} (${tier})`,
              got: Math.round(th.getBoundingClientRect().width),
              want: parseFloat(root.getPropertyValue(`--column-width-${tier}`))
            }
          ]
        : [];
    });
  });

const isTable = (name: string) => TABLE_PAGES.some((r) => r.name === name);

for (const route of ALL_PAGES) {
  test.describe(`page: ${route.name}`, () => {
    // One worker runs the page's tests in turn, so they share the one load; a failure only costs a reload.
    test.describe.configure({ mode: "default" });
    let context: BrowserContext;
    let page: Page;

    test.beforeAll(async ({ browser }: { browser: Browser }) => {
      context = await newAdminContext(browser);
      page = await context.newPage();
      await openPage(page, route.path);
    });

    // The page is not a fixture, so Playwright's own failure screenshot and trace do not cover it.
    test.afterEach(async ({}, testInfo) => {
      if (testInfo.status !== testInfo.expectedStatus) {
        await testInfo.attach("url", { body: page.url(), contentType: "text/plain" });
        await testInfo.attach("page", {
          body: await page.screenshot().catch(() => Buffer.alloc(0)),
          contentType: "image/png"
        });
      }
    });

    test.afterAll(async () => {
      await context?.close();
    });

    test("language, title, one main and a navigation landmark", async () => {
      expect(await page.locator("html").getAttribute("lang")).toMatch(/^[a-z]{2}/);
      expect((await page.title()).trim()).not.toBe("");
      expect(await page.locator("main, [role='main']").count(), "one main landmark").toBe(1);
      expect(await page.locator("nav, [role='navigation']").count()).toBeGreaterThan(0);
    });

    test("the table has a name and its sortable headers say how they are sorted", async () => {
      if (isTable(route.name)) {
        // Either the table or the panel of an empty list; a page showing neither has lost its content.
        if (!(await expectTableOrState(page))) {
          return;
        }
      } else {
        test.skip(!(await hasTable(page)), "no table on this page");
      }
      const unnamed = await page.evaluate(() =>
        [...document.querySelectorAll<HTMLElement>(".table-scroll-region table")]
          .filter(
            (t) => !t.getAttribute("aria-label") && !t.getAttribute("aria-labelledby") && !t.querySelector("caption")
          )
          .map((t) => t.className)
      );
      expect.soft(unnamed, "tables without a name").toEqual([]);
      const missing = await page
        .locator("th.mat-sort-header")
        .evaluateAll((ths) => ths.filter((t) => !t.getAttribute("aria-sort")).map((t) => t.textContent?.trim()));
      expect.soft(missing, "sortable headers without aria-sort").toEqual([]);
    });

    test("every control is announced with a name and the headings form an outline", async () => {
      const snapshot = await page.locator("body").ariaSnapshot();
      expect.soft(snapshot.match(UNNAMED) ?? [], "controls without a name").toEqual([]);

      // The page is named by one h1; the headings the page draws itself follow, each at most one level below the last.
      // The h1 is read, not drawn: a clipped 1px box that takes no room.
      const h1Box = await page.getByRole("heading", { level: 1 }).first().boundingBox();
      expect.soft(h1Box?.height ?? 0, "the h1 is hidden visually").toBeLessThanOrEqual(2);
      const levels = [...snapshot.matchAll(HEADING)].map((m) => Number(m[1]));
      expect.soft(levels.filter((l) => l === 1).length, "one h1").toBe(1);
      expect.soft(levels[0], "the h1 comes first").toBe(1);
      const own = levels.slice(1);
      const jumps = own.flatMap((l, i) => (i > 0 && l > own[i - 1] + 1 ? [`h${own[i - 1]} -> h${l}`] : []));
      expect.soft(jumps, "heading jumps").toEqual([]);
    });

    test("nothing keeps animating under reduced motion", async () => {
      await settle(page);
      const moving = await page.evaluate(() =>
        document
          .getAnimations()
          .filter((a) => a.playState === "running")
          .map((a) => {
            const target = (a.effect as KeyframeEffect | null)?.target as HTMLElement | null;
            return {
              element: target,
              name: (a as CSSAnimation).animationName ?? (a as CSSTransition).transitionProperty
            };
          })
          .filter(
            ({ element }) =>
              !element?.closest(
                "mat-progress-bar, mat-progress-spinner, mat-spinner, .mat-ripple, .mdc-linear-progress"
              )
          )
          .map(
            ({ element, name }) =>
              `${element?.tagName.toLowerCase()}.${String(element?.className).split(" ")[0]}: ${name}`
          )
      );
      expect(moving).toEqual([]);
    });

    if (isTable(route.name)) {
      test("a col-width-* column is never narrower than its tier", async () => {
        const tiers = await tierWidths(page);
        if (tiers.length === 0 && !(await expectTableOrState(page))) {
          return;
        }
        expect(tiers.length, "the table has a col-width-* column").toBeGreaterThan(0);
        expect(tiers.filter((c) => c.got < c.want - 1)).toEqual([]);
      });

      test("a col-width-* column is exactly its tier wide", async () => {
        knownFailure(test, "tier width", route.name);
        const tiers = await tierWidths(page);
        if (tiers.length === 0 && !(await expectTableOrState(page))) {
          return;
        }
        expect(tiers.length, "the table has a col-width-* column").toBeGreaterThan(0);
        expect(tiers.filter((c) => Math.abs(c.got - c.want) > 1)).toEqual([]);
      });
    }

    test("Tab moves through the page without losing or trapping focus", async () => {
      await resetFocusStart(page);
      const seen: string[] = [];
      const problems: string[] = [];

      for (let i = 0; i < 60; i++) {
        await page.keyboard.press("Tab");
        const info = await page.evaluate(() => {
          const e = document.activeElement as HTMLElement | null;
          if (!e || e === document.body) {
            return null;
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
        if (!info) {
          // Focus left the controls for the document or the browser's own UI: the end of the page, or a page that
          // re-rendered; Tab goes on.
          continue;
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

    test("a keyboard-focused control shows a focus indicator", async () => {
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      await resetFocusStart(page);
      const { misses, checked } = await focusIndicatorMisses(page);
      expect(checked, "controls of the page content checked").toBeGreaterThanOrEqual(3);
      expect(misses).toEqual([]);
    });

    test("the layout holds at every zoom and at 320 CSS px", async () => {
      const row: Locator = page.locator("tr.mat-mdc-row").first();
      const label: Locator = page.locator(".mat-mdc-paginator-range-label").first();
      const hasRow = (await row.count()) > 0;
      const hasLabel = (await label.count()) > 0;
      const table = isTable(route.name) && (await expectTableOrState(page));

      try {
        for (const zoom of ZOOMS) {
          await page.setViewportSize(sized(zoom));
          await settle(page);
          const at = `${Math.round(zoom * 100)}% zoom`;
          expect.soft(await sideways(page), `${at}: the page itself scrolls sideways by`).toBeLessThanOrEqual(1);
          if (table) {
            expect.soft(await spill(page), `${at}: the filter row spills out of its card by`).toBeLessThanOrEqual(1);
          }
          if (hasLabel) {
            // "1 – 15 of 10239": the range and the total. The compact range gives the total up before the filter field
            // shrinks, so at 200% zoom (960 CSS px) the range alone has to show.
            const text = (await label.textContent()) ?? "";
            const pattern = zoom < 2 ? /\d[\d.,]*\D+\d[\d.,]*\D+\d[\d.,]*/ : /\d[\d.,]*\D+\d[\d.,]*/;
            expect.soft(text, `${at}: the paginator label`).toMatch(pattern);
          }
          // Hovering a row reveals its cell actions; the columns must not move for them, least of all in a narrow
          // window, where a column the card squeezes below its tier would follow its content.
          if (table && hasRow && (zoom === 1 || zoom === 1.5)) {
            await page.mouse.move(0, 0);
            const rest = await columnWidths(page);
            await row.hover();
            await settle(page);
            expect.soft(await columnWidths(page), `${at}: hovering a row resizes the columns`).toEqual(rest);
            await page.mouse.move(0, 0);
          }
        }

        // WCAG 1.4.10 Reflow: 320 CSS px, a 1280px window at 400% zoom. A table may scroll inside its region.
        await page.setViewportSize({ width: 320, height: 568 });
        await settle(page);
        expect.soft(await sideways(page), "320 CSS px: the page itself scrolls sideways by").toBeLessThanOrEqual(1);
      } finally {
        await page.setViewportSize({ width: SCREEN.width, height: SCREEN.height });
        await settle(page);
      }
    });
  });
}

test.describe("pages are told apart", () => {
  test("each page has a title of its own that names it", async ({ page }) => {
    test.setTimeout(900_000);
    const titles = new Map<string, string>();
    for (const route of ALL_PAGES) {
      await openPage(page, route.path);
      titles.set(route.name, await page.title());
    }
    const duplicates = [...titles]
      .filter(([, t], i, all) => all.findIndex(([, other]) => other === t) !== i)
      .map(([name, t]) => `${name}: ${t}`);
    expect(duplicates).toEqual([]);
  });
});
