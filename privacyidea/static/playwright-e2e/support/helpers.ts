import { expect, Page } from "@playwright/test";

// Opens a page and waits until its content (table, form or panel) has rendered and settled.
export async function openPage(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "networkidle" });
  // A lost session redirects to the login page, which would pass every check below for the wrong page.
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page.locator(".admin-content").first()).toBeVisible();
  // Loading indicators come and go with the data; a page measured while one shows is not the settled page.
  await expect(page.locator("mat-spinner, mat-progress-spinner, mat-progress-bar"))
    .toHaveCount(0, { timeout: 5_000 })
    .catch(() => undefined);
  await page.waitForTimeout(400);
}

export interface TableBox {
  card: number;
  region: number;
  table: number;
  rows: number;
}

export async function hasTable(page: Page): Promise<boolean> {
  return (await page.locator(".table-scroll-region table").count()) > 0;
}

// Widths of the page's table card, its scroll region and the table, in whole pixels.
export async function measureTable(page: Page): Promise<TableBox> {
  return page.evaluate(() => {
    const region = document.querySelector<HTMLElement>(".table-scroll-region")!;
    const table = region.querySelector("table")!;
    const w = (e: Element) => Math.round(e.getBoundingClientRect().width);
    return {
      card: w(region.parentElement!),
      region: w(region),
      table: w(table),
      rows: region.querySelectorAll("tr.mat-mdc-row").length
    };
  });
}

// Forces the sticky-header state the way ScrollEdgesDirective does once a table scrolls, so it shows even on
// a table with too few rows to scroll.
export async function setSticky(page: Page, on: boolean): Promise<void> {
  await page.evaluate((on) => {
    const region = document.querySelector(".table-scroll-region")!;
    region.classList.toggle("scrolled-from-top", on);
    region.classList.toggle("controls-collapsed", on);
  }, on);
  await page.waitForTimeout(250);
}

export function filterInput(page: Page) {
  return page.locator(".filter-paginator-container input, app-policy-filter input").first();
}

// Backend calls the shell of the app needs to render at all; everything else a page loads can be held or failed.
const SHELL_ENDPOINTS = [
  "config",
  "auth",
  "user/settings",
  "realm",
  "defaultrealm",
  "info/integrations",
  "container/types",
  "policy/defs"
];

// Fails ("error") or never answers ("loading") the GET requests a page loads its data with, so the page stays in the
// error or loading state of its table panel. Held requests are dropped when the test ends.
export async function holdApi(page: Page, mode: "error" | "loading"): Promise<void> {
  await page.route("**/proxy/**", (route) => {
    const request = route.request();
    const endpoint = new URL(request.url()).pathname.replace(/^.*\/proxy\//, "");
    if (request.method() !== "GET" || SHELL_ENDPOINTS.some((e) => endpoint.startsWith(e))) {
      return route.continue();
    }
    if (mode === "error") {
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          result: { status: false, error: { code: 1, message: "Forced by the e2e test" } },
          id: 1
        })
      });
    }
    return undefined;
  });
}
