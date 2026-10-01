# WebUI end-to-end tests (Playwright)

Browser tests for the layout, style and accessibility of the WebUI. They run against an already running WebUI and
backend and only read: they log in, visit pages, type into filters and open menus, and never save anything.

```
npm run test:e2e            # everything
npm run test:e2e:a11y       # axe only
npx playwright test --config playwright-e2e/playwright.config.ts layout -g "policies"
npx playwright show-report playwright-e2e/playwright-report
```

| Variable   | Default                          |
| ---------- | -------------------------------- |
| `BASE_URL` | `https://localhost:4200/app/v2/` |
| `E2E_USER` | `admin`                          |
| `E2E_PASS` | `admin`                          |

The browser is Chromium (`npx playwright install chromium`). The instance should hold some data: tests on empty
tables skip their row-dependent checks rather than fail.

## Specs

- `accessibility.spec.ts` - axe-core (WCAG 2.2 A/AA) on every page, light and dark theme.
- `keyboard.spec.ts` - document structure, table names and `aria-sort`, Tab order and focus visibility, menu focus.
- `layout.spec.ts` - at 100/125/150/200% zoom: no sideways page scroll, filter row inside its card, paginator total;
  and: table and card width unchanged by filtering, sticky header or row hover, `col-width-*` tiers exact, sticky
  header position.

## The accessibility baseline

The WebUI does not pass axe yet. `accessibility-baseline.json` lists, per page and theme, the rules known to fail,
so the suite fails on a rule that is new to a page and stays green on the existing backlog. After fixing a rule,
regenerate the file (`npm run test:e2e:baseline`, one worker) and review the diff: it removes what you fixed, and
also records anything that regressed.

A test marked `test.fail()` is a known failure that should start passing; when it does, Playwright reports it,
and the marker goes.
