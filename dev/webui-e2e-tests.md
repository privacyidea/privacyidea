# WebUI end-to-end tests (Playwright)

Browser tests for the layout, style and accessibility of the WebUI. They live in `privacyidea/static/playwright-e2e/`
and run against an already running WebUI and backend. They only read: they log in, visit pages, type into filters and
open menus, and never save anything.

All commands run in `privacyidea/static`, and all paths below are relative to that directory.

```
npm run test:e2e            # everything
npm run test:e2e:a11y       # axe only
npx playwright test --config playwright-e2e/playwright.config.ts layout -g "policies"
npx playwright show-report playwright-e2e/playwright-report/<run id>
```

Every run writes its HTML report to `playwright-e2e/playwright-report/<run id>` and its artifacts to
`playwright-e2e/test-results/<run id>`, where the run id is the process id of the run. Both directories and the stored
login session (`playwright-e2e/.auth/`) are ignored by git.

| Variable                          | Default                                                   |
| --------------------------------- | --------------------------------------------------------- |
| `BASE_URL`                        | `https://localhost:4200/app/v2/`                          |
| `E2E_USER`                        | `admin`                                                   |
| `E2E_PASS`                        | `admin`                                                   |
| `E2E_SELF_USER` / `E2E_SELF_PASS` | a self-service user for `self-service.spec.ts` (optional) |
| `E2E_WORKERS`                     | `8`, the number of pages tested side by side              |

The browser is Chromium (`npx playwright install chromium`). The instance should hold some data: tests on empty
tables skip their row-dependent checks rather than fail.

## Specs

- `playwright-e2e/pages.spec.ts` - the main spec. Every page is loaded once and all of its checks run against that
  load: language, title and landmarks, table name and `aria-sort`, the accessibility tree (names, heading outline),
  nothing animating under reduced motion, `col-width-*` tiers, Tab order, a visible focus indicator on the controls of
  the page content, and last the layout at 100/125/150/200% browser zoom and at 320 CSS px (no sideways page scroll,
  filter row inside its card, paginator range, columns stable under row hover). A last test checks that every page has
  a title of its own. A failing test attaches the URL and a screenshot of the shared page.
- `playwright-e2e/accessibility.spec.ts` - axe-core (WCAG 2.2 A/AA) on every page, light and dark theme.
- `playwright-e2e/login.spec.ts` - the login page without a session: axe in both themes, the heading that names the
  page, and the keyboard order of the form.
- `playwright-e2e/states.spec.ts` - the panel a table shows while loading, after an error, on an instance without data
  and when a filter matches nothing, in both themes (axe, accessible names, heading and retry button). The backend is
  held, failed or answered with an empty list by route interception. Every table page must show the panel; the realms
  page is skipped (its list comes from an endpoint the app shell needs) as are pages without a filter for the filtered
  state.
- `playwright-e2e/details.spec.ts` - the detail and edit pages, reached from the first row of their list: axe in both
  themes, landmarks, Tab order and no sideways scroll at each zoom. A list without rows skips its tests; a click on a
  row that does not open a `/details/` or `/edit/` page fails.
- `playwright-e2e/overlays.spec.ts` - menus (opened from the keyboard, first item focused, Escape returns focus, items
  named, axe on the overlay) and the delete confirmations (named, focus trapped, Escape closes; nothing is confirmed),
  in both themes.
- `playwright-e2e/motion.spec.ts` - focus stays marked in forced colors.
- `playwright-e2e/layout.spec.ts` - table and card width unchanged by filtering or the sticky header, and the sticky
  header position.
- `playwright-e2e/self-service.spec.ts` - the self-service pages, with `E2E_SELF_USER` / `E2E_SELF_PASS`; skipped
  without them.

The page lists the specs iterate over are in `playwright-e2e/support/routes.ts`; a new page has to be added there to be
covered.

The theme of a run is the emulated colour scheme. The app applies the theme stored with the user ahead of
`prefers-color-scheme`, so `openPage` (and every spec that navigates by itself) calls `forceTheme`, which puts the
`light` or `dark` class on `<html>` without writing the setting and asserts that the page really renders in that theme.

The focus check (`playwright-e2e/support/focus.ts`) tabs past the shell until it has checked 40 controls inside the
page content (at most 150 stops) and reports how many it checked; the tests require at least three. It compares each
focused control with the same control unfocused, with the text caret hidden.

Not covered: the localized builds (the dev server serves English only) and the real output of a screen reader.

## The accessibility baseline

The WebUI does not pass axe yet. `playwright-e2e/accessibility-baseline.json` lists, per page and theme, the rules
known to fail, so the suite fails on a rule that is new to a page and stays green on the existing backlog. After fixing
a rule, regenerate the file (`npm run test:e2e:baseline`; it records every axe check of the suite) and review the diff:
it removes what you fixed, and also records anything that regressed.

A test marked `test.fail()` is a known failure that should start passing; when it does, Playwright reports it,
and the marker goes.
