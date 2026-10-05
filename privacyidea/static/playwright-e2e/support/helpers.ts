import { expect, Page } from "@playwright/test";

// Opens a page and waits until its content (table, form or panel) has rendered and settled.
export async function openPage(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "networkidle" });
  await expectAdminPage(page);
  // Loading indicators come and go with the data; a page measured while one shows is not the settled page.
  await expect(page.locator("mat-spinner, mat-progress-spinner, mat-progress-bar"))
    .toHaveCount(0, { timeout: 5_000 })
    .catch(() => undefined);
  await settle(page);
  await forceTheme(page);
}

// Asserts the page is an admin page and not the login a lost session redirects to, which would pass every check for
// the wrong page.
export async function expectAdminPage(page: Page): Promise<void> {
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page.locator(".admin-content").first()).toBeVisible();
}

// Makes the page wear the theme the browser emulates (colorScheme of the test). The app applies the theme stored with
// the user ahead of prefers-color-scheme, so without this a "dark" run audits whatever the stored setting is. The
// classes on <html> are the ones ThemeService sets (light / dark, which carry color-scheme and the theme tokens);
// nothing is written to the backend. Asserts that the page really renders in that theme.
export async function forceTheme(page: Page): Promise<void> {
  const scheme = await page.evaluate(() => {
    const wanted = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    const root = document.documentElement;
    root.classList.remove("light", "dark", "system");
    root.classList.add(wanted);
    return wanted;
  });
  // Forced colors replace the page's colours with system colors; only the classes can be asserted then.
  const forced = await page.evaluate(() => matchMedia("(forced-colors: active)").matches);
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const root = document.documentElement;
          // The body's own background, or the root's where the body is transparent.
          const paint =
            [document.body, root]
              .map((e) => getComputedStyle(e).backgroundColor)
              .find((c) => !/rgba\(.*,\s*0\)$/.test(c)) ?? "rgb(255, 255, 255)";
          const [r, g, b] = (paint.match(/[\d.]+/g) ?? ["255", "255", "255"]).map(Number);
          const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
          return {
            classes: ["light", "dark", "system"].filter((c) => root.classList.contains(c)),
            colorScheme: getComputedStyle(root).colorScheme,
            background: luminance < 0.5 ? "dark" : "light"
          };
        }),
      { message: `the page renders in the ${scheme} theme` }
    )
    .toEqual(
      forced
        ? expect.objectContaining({ classes: [scheme] })
        : { classes: [scheme], colorScheme: scheme, background: scheme }
    );
}

// Waits until the page has laid itself out after a change of size or state: two animation frames, so style and layout
// have run, and a short pause for the observers (ResizeObserver, the paginator's compact range) that answer them.
export async function settle(page: Page): Promise<void> {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 150))))
  );
}

// For a page that is a table page: whether it shows its table (true) or the panel of an empty or failed list (false).
// A page with neither has lost its content, which fails the test instead of skipping it.
export async function expectTableOrState(page: Page): Promise<boolean> {
  const table = await hasTable(page);
  if (!table) {
    expect(
      await page.locator(".table-state").count(),
      "a table page shows its table or a table-state panel"
    ).toBeGreaterThan(0);
  }
  return table;
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
  await settle(page);
}

export function filterInput(page: Page) {
  return page.locator(".filter-paginator-container input, app-policy-filter input").first();
}

// Types `text` into the page's filter and applies it: the server-side filters (tokens, containers, locked users) apply
// on Enter, the others as the text changes, and Enter is harmless to those.
export async function applyFilter(page: Page, text: string): Promise<void> {
  const input = filterInput(page);
  await input.fill(text);
  await input.press("Enter");
}

// Backend calls the shell of the app needs to render at all; everything else a page loads can be held or failed.
const SHELL_ENDPOINTS = [
  "config",
  "auth/rights",
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

// Puts the starting point of sequential focus navigation back at the top of the document, so that the next Tab lands
// on the first control instead of the one after whatever had focus last.
export async function resetFocusStart(page: Page): Promise<void> {
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    const marker = document.createElement("div");
    marker.tabIndex = -1;
    document.body.prepend(marker);
    marker.focus();
    marker.remove();
  });
}

const PAGED = { count: 0, current: 1, next: null, prev: null };

// The GET request each table page loads its rows with (the path after /proxy/, no query) and what a privacyIDEA
// instance without data answers to it. Requests of the same page for other things (realms, resolvers, filter
// choices) are left alone.
const EMPTY_LISTS: Record<string, { endpoint: string; value: unknown }> = {
  tokens: { endpoint: "token/", value: { ...PAGED, tokens: [] } },
  challenges: { endpoint: "token/challenges/", value: { ...PAGED, challenges: [], redis_cache_enabled: false } },
  containers: { endpoint: "container/", value: { ...PAGED, containers: [] } },
  "container templates": { endpoint: "container/templates", value: { templates: [] } },
  users: { endpoint: "user/", value: [] },
  resolvers: { endpoint: "resolver/", value: {} },
  policies: { endpoint: "policy/", value: [] },
  "conditional access": { endpoint: "conditionalaccess/policy", value: [] },
  "api clients": { endpoint: "clients/", value: [] },
  events: { endpoint: "event/", value: [] },
  machines: { endpoint: "machine/", value: [] },
  "machine resolvers": { endpoint: "machineresolver/", value: {} },
  "periodic tasks": { endpoint: "periodictask/", value: [] },
  audit: { endpoint: "audit/", value: { ...PAGED, auditcolumns: [], auditdata: [] } },
  "authentication log": { endpoint: "authenticationlog/", value: { ...PAGED, auth_logs: [] } },
  clients: { endpoint: "client/", value: {} },
  "locked users": { endpoint: "conditionalaccess/lock/users", value: { ...PAGED, locked_users: [] } },
  blocklist: { endpoint: "conditionalaccess/blocklist", value: [] },
  "smtp servers": { endpoint: "smtpserver/", value: {} },
  "radius servers": { endpoint: "radiusserver/", value: {} },
  "sms gateways": { endpoint: "smsgateway/", value: [] },
  "privacyidea servers": { endpoint: "privacyideaserver/", value: {} },
  "ca connectors": { endpoint: "caconnector/", value: [] },
  tokengroups: { endpoint: "tokengroup/", value: {} },
  "service ids": { endpoint: "serviceid/", value: {} }
};

// Whether emptyApi knows the list endpoint of the table page `name`.
export function hasEmptyList(name: string): boolean {
  return name in EMPTY_LISTS;
}

// Answers the list request of the table page `name` with a valid response that holds no rows, so the page shows the
// panel of an instance without data (app-table-state, status "empty"). The rest of the backend stays real.
export async function emptyApi(page: Page, name: string): Promise<void> {
  const list = EMPTY_LISTS[name];
  await page.route("**/proxy/**", (route) => {
    const request = route.request();
    const endpoint = new URL(request.url()).pathname.replace(/^.*\/proxy\//, "");
    if (request.method() !== "GET" || endpoint !== list.endpoint) {
      return route.continue();
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 1,
        jsonrpc: "2.0",
        result: { status: true, value: list.value },
        time: 0,
        version: "e2e"
      })
    });
  });
}
