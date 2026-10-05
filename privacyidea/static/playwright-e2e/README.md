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
| `E2E_SELF_USER` / `E2E_SELF_PASS` | a self-service user for `self-service.spec.ts` (optional) |

The browser is Chromium (`npx playwright install chromium`). The instance should hold some data: tests on empty
tables skip their row-dependent checks rather than fail.

## Specs

- `accessibility.spec.ts` - axe-core (WCAG 2.2 A/AA) on every page, light and dark theme.
- `states.spec.ts` - the panel a table shows while loading, after an error and when a filter matches nothing (axe,
  accessible names, heading and retry button). The backend is held or failed with route interception.
- `details.spec.ts` - the detail and edit pages, reached from the first row of their list: axe, landmarks, Tab order and
  no sideways scroll at 100/150/200% zoom.
- `overlays.spec.ts` - menus (opened from the keyboard, first item focused, Escape returns focus, items named, axe on the
  overlay) and the delete confirmations (named, focus trapped, Escape closes; nothing is confirmed).
- `keyboard.spec.ts` - document structure, table names and `aria-sort`, Tab order and focus visibility, menu focus.
- `screenreader.spec.ts` - the accessibility tree: every control has a name, the headings form an outline.
- `motion.spec.ts` - nothing keeps animating under `prefers-reduced-motion`; focus stays marked in forced colors.
- `reflow.spec.ts` - WCAG 1.4.10, no sideways page scroll at 320 CSS px.
- `layout.spec.ts` - at 100/125/150/200% zoom: no sideways page scroll, filter row inside its card, paginator range
  (and total up to 150%); and: table and card width unchanged by filtering, sticky header or row hover, `col-width-*`
  tiers, sticky header position.
- `self-service.spec.ts` - the self-service pages, with `E2E_SELF_USER` / `E2E_SELF_PASS`; skipped without them.

Not covered: the localized builds (the dev server serves English only), the real output of a screen reader, and
empty tables (the instance's data decides whether a list has rows).

## The accessibility baseline

The WebUI does not pass axe yet. `accessibility-baseline.json` lists, per page and theme, the rules known to fail,
so the suite fails on a rule that is new to a page and stays green on the existing backlog. After fixing a rule,
regenerate the file (`npm run test:e2e:baseline`, one worker) and review the diff: it removes what you fixed, and
also records anything that regressed.

A test marked `test.fail()` is a known failure that should start passing; when it does, Playwright reports it,
and the marker goes.
