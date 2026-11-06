# WebUI accessibility checks in the component tests

The WebUI component tests (Jest) can run [axe-core](https://github.com/dequelabs/axe-core) on a rendered component. axe
checks the names, roles and ARIA attributes of the elements against the WCAG 2.2 Level A and AA rules. A check fails the
test if it finds a violation.

The checks run with `npm test` in `privacyidea/static`, like every other component test. They need no browser and no
backend.

## Adding a check

```ts
import { axe } from "@testing/axe";

it("passes the axe accessibility checks", async () => {
  fixture.detectChanges();

  expect(await axe(fixture.nativeElement)).toHaveNoViolations();
});
```

Add a check:

- to every new component with interactive elements (buttons, links, form fields, toggles)
- when a change adds or removes names, roles or ARIA attributes

One check per component is enough. Add another one only for a state that renders different controls, for example a table
with an expanded row, or a view for admins and one for users.

Material overlays (dialogs, menus, tooltips) are not rendered inside the component, but in the overlay container at the
end of the document. To check an open dialog or menu, pass that container to `axe`, not `fixture.nativeElement`.

The helper is `src/testing/axe.ts`. It registers nothing globally; the `toHaveNoViolations` matcher is registered in
`src/jest.setup.ts`.

## How it works

1. The test renders the component into the jsdom document, with mocked services and test data.
2. `axe(element)` runs axe-core on that element and its children. For each element, axe determines what assistive
   technology would get: the role (button, link, textbox, ...), the accessible name (from `aria-labelledby`,
   `aria-label`, `<label>`, the text content, `alt`, ...) and the ARIA attributes.
3. axe compares this with its rules. `toHaveNoViolations()` fails if a rule is violated. The message names the rule, the
   element and what is missing.

The helper runs only the rules tagged as WCAG 2.0, 2.1 and 2.2, Level A and AA (about 70 rules).

## What it finds

Examples:

| Rule | Finds |
|---|---|
| `button-name`, `link-name`, `aria-command-name` | a button or link without a name, e.g. an unlabelled icon button |
| `label` | a form field without a label, e.g. a field with only a placeholder |
| `aria-allowed-attr`, `aria-prohibited-attr` | an ARIA attribute the role forbids, e.g. `aria-label` on a plain `div` |
| `aria-valid-attr-value` | `aria-labelledby`, `aria-describedby` or `aria-controls` with an id that does not exist |
| `nested-interactive` | an interactive element inside another one, e.g. a button inside an expansion panel header |
| `aria-required-children`, `aria-required-parent` | wrong structure, e.g. a `role="row"` outside a table |
| `aria-hidden-focus` | a focusable element inside `aria-hidden="true"` |
| `image-alt` | an image without `alt` |

## What it does not find

- **Behaviour.** axe does not press keys or move the focus. Whether Space triggers a toggle, whether the focus stays
  after a reload, or in which order Tab moves, needs a normal test assertion or a browser test.
- **Layout.** jsdom does not lay out the page. Colour contrast, a visible focus ring, target size, zoom and reflow, and
  sticky headers covering the focus are not checked. The colour rules are turned off for this reason.
- **The page around the component.** Landmarks and the heading order of a page are not checked. axe tags these rules as
  best practice, not as WCAG, so the helper does not run them.
- **States the test does not render.** A dialog that never opens in the test is not checked.
- **What a screen reader really says.** A passing check means that axe found no errors, not that the component is
  accessible.

These parts are covered by the Playwright suite, which runs axe and further checks on the real pages in a browser, and
by a manual keyboard and screen-reader test.

## Pitfalls

- **Empty mocks.** If a mocked service returns no text, a component can look unnamed to axe, e.g. a state toggle whose
  text comes from a mocked `TableUtilsService`. Give the mock a realistic value in the test
  (`mockReturnValue("Active")`); don't turn off the rule.
- **Timeout.** axe can take more than a second on a large form, and two to three times longer when all Jest workers
  are busy, which can exceed the default timeout of 5 seconds. If the check takes more than half a second when the
  spec runs alone, pass `AXE_TIMEOUT` from the helper as the third argument of its `it`.
- **Fake timers.** axe needs real timers. A test that calls `jest.useFakeTimers()` must switch back with
  `jest.useRealTimers()` (e.g. in `afterEach`). Otherwise the axe check in a later test of the same file hangs until the
  test timeout.

## Known violations

If a component has a violation that is not fixed yet, turn off only that one rule for this check, and say why and which
issue fixes it:

```ts
// Buttons inside the panel header; fixed by #1234.
expect(await axe(element, { rules: { "nested-interactive": { enabled: false } } })).toHaveNoViolations();
```

Turn the rule on again in the change that fixes it.
