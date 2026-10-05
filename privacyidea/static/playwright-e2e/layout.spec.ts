import { expect, test } from "./support/test";
import { TABLE_PAGES } from "./support/routes";
import {
  applyFilter,
  expectTableOrState,
  filterInput,
  measureTable,
  openPage,
  setSticky,
  settle
} from "./support/helpers";

test.describe("table width stays put", () => {
  for (const route of TABLE_PAGES) {
    test(`${route.name}: filtering and the sticky header do not resize the table or its card`, async ({ page }) => {
      await openPage(page, route.path);
      test.skip(!(await expectTableOrState(page)), "the list is empty, the page shows its empty state");
      const input = filterInput(page);
      test.skip((await input.count()) === 0, "no filter on this page");

      const rest = await measureTable(page);
      const states: [string, Awaited<ReturnType<typeof measureTable>>][] = [];

      await setSticky(page, true);
      states.push(["sticky", await measureTable(page)]);
      await setSticky(page, false);

      for (const filter of ["zzzzqq", ""]) {
        await applyFilter(page, filter);
        await page.waitForLoadState("networkidle");
        await settle(page);
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

test.describe("sticky header", () => {
  test.use({ viewport: { width: 1920, height: 560 } });

  for (const route of TABLE_PAGES) {
    test(`${route.name}: the header stays at the top of the scroll region`, async ({ page }) => {
      await openPage(page, route.path);
      test.skip(!(await expectTableOrState(page)), "the list is empty, the page shows its empty state");
      const region = page.locator(".table-scroll-region").first();
      const scrollable = await region.evaluate((r) => r.scrollHeight - r.clientHeight > 80);
      test.skip(!scrollable, "table too short to scroll here");

      await region.evaluate((r) => (r.scrollTop = 60));
      await settle(page);
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
