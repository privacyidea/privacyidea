import { expect, test } from "./support/test";
import { OTHER_PAGES, SCREEN, TABLE_PAGES, ZOOMS } from "./support/routes";
import { knownFailure } from "./support/known";
import { filterInput, hasTable, measureTable, openPage, setSticky } from "./support/helpers";

const zoomed = (zoom: number) => ({
  viewport: { width: Math.round(SCREEN.width / zoom), height: Math.round(SCREEN.height / zoom) },
  deviceScaleFactor: zoom
});

// Browser zoom as Chrome applies it on a 1920x1080 screen: the CSS viewport shrinks, the pixel ratio grows.
for (const zoom of ZOOMS) {
  test.describe(`at ${Math.round(zoom * 100)}% zoom`, () => {
    test.use(zoomed(zoom));

    for (const route of [...TABLE_PAGES, ...OTHER_PAGES]) {
      test(`${route.name}: the page itself never scrolls sideways`, async ({ page }) => {
        await openPage(page, route.path);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        expect(overflow).toBeLessThanOrEqual(1);
      });
    }

    for (const route of TABLE_PAGES) {
      test(`${route.name}: filter row and paginator stay inside the card`, async ({ page }) => {
        await openPage(page, route.path);
        test.skip(!(await hasTable(page)), "no table on this instance");
        const spill = await page.evaluate(() => {
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
        expect(spill).toBeLessThanOrEqual(1);
      });

      test(`${route.name}: the paginator shows its range${zoom < 2 ? " and total" : ""}`, async ({ page }) => {
        await openPage(page, route.path);
        const label = page.locator(".mat-mdc-paginator-range-label").first();
        test.skip((await label.count()) === 0, "no paginator on this page");
        // "1 – 15 of 10239": the page's own range and the total. PaginatorCompactRangeDirective gives the total up
        // before the filter field shrinks, so at 200% zoom (960 CSS px) the range alone is what has to show.
        await expect(label).toHaveText(zoom < 2 ? /\d[\d.,]*\D+\d[\d.,]*\D+\d[\d.,]*/ : /\d[\d.,]*\D+\d[\d.,]*/);
      });
    }
  });
}

test.describe("table width stays put", () => {
  for (const route of TABLE_PAGES) {
    test(`${route.name}: filtering and the sticky header do not resize the table or its card`, async ({ page }) => {
      await openPage(page, route.path);
      test.skip(!(await hasTable(page)), "no table on this instance");
      const input = filterInput(page);
      test.skip((await input.count()) === 0, "no filter on this page");

      const rest = await measureTable(page);
      const states: [string, Awaited<ReturnType<typeof measureTable>>][] = [];

      await setSticky(page, true);
      states.push(["sticky", await measureTable(page)]);
      await setSticky(page, false);

      for (const filter of ["zzzzqq", ""]) {
        await input.fill(filter);
        await page.waitForTimeout(900);
        states.push([`filter "${filter}"`, await measureTable(page)]);
        await setSticky(page, true);
        states.push([`filter "${filter}" + sticky`, await measureTable(page)]);
        await setSticky(page, false);
      }

      for (const [label, box] of states) {
        expect.soft({ card: box.card, table: box.table }, label).toEqual({ card: rest.card, table: rest.table });
      }
    });
  }
});

// Hovering reveals a row's cell actions; the columns must not move for them, least of all in a narrow window,
// where a column that the card squeezes below its tier would follow its content.
for (const zoom of [1, 1.5] as const) {
  test.describe(`row hover at ${Math.round(zoom * 100)}% zoom`, () => {
    test.use(zoomed(zoom));

    for (const route of TABLE_PAGES) {
      test(`${route.name}: hovering a row does not resize its columns`, async ({ page }) => {
        await openPage(page, route.path);
        const row = page.locator("tr.mat-mdc-row").first();
        test.skip((await row.count()) === 0, "no rows on this instance");
        const columns = () =>
          page.evaluate(() =>
            [...document.querySelectorAll("th")].map((t) => Math.round(t.getBoundingClientRect().width))
          );
        const rest = await columns();
        await row.hover();
        await page.waitForTimeout(300);
        expect(await columns()).toEqual(rest);
      });
    }
  });
}

test.describe("column tiers", () => {
  const tierWidths = (page: import("@playwright/test").Page) =>
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

  for (const route of TABLE_PAGES) {
    test(`${route.name}: a col-width-* column is never narrower than its tier`, async ({ page }) => {
      await openPage(page, route.path);
      const narrow = (await tierWidths(page)).filter((c) => c.got < c.want - 1);
      expect(narrow).toEqual([]);
    });

    test(`${route.name}: a col-width-* column is exactly its tier wide`, async ({ page }) => {
      knownFailure(test, "tier width", route.name);
      await openPage(page, route.path);
      const off = (await tierWidths(page)).filter((c) => Math.abs(c.got - c.want) > 1);
      expect(off).toEqual([]);
    });
  }
});

test.describe("sticky header", () => {
  test.use({ viewport: { width: 1920, height: 560 } });

  for (const route of TABLE_PAGES) {
    test(`${route.name}: the header stays at the top of the scroll region`, async ({ page }) => {
      await openPage(page, route.path);
      const region = page.locator(".table-scroll-region").first();
      test.skip((await region.count()) === 0, "no table on this instance");
      const scrollable = await region.evaluate((r) => r.scrollHeight - r.clientHeight > 80);
      test.skip(!scrollable, "table too short to scroll here");

      await region.evaluate((r) => (r.scrollTop = 60));
      await page.waitForTimeout(300);
      const gap = await page.evaluate(() => {
        const r = document.querySelector(".table-scroll-region")!.getBoundingClientRect();
        const h = document.querySelector("th")!.getBoundingClientRect();
        return Math.abs(h.top - r.top);
      });
      // The region's own 1px top border sits above the header.
      expect(gap).toBeLessThanOrEqual(2);
    });
  }
});
