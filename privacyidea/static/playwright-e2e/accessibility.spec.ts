import { test } from "./support/test";
import { ALL_PAGES } from "./support/routes";
import { openPage } from "./support/helpers";
import { expectNoNewViolations } from "./support/axe";

// Every page, in the light and the dark theme. See support/axe.ts for the baseline.
for (const scheme of ["light", "dark"] as const) {
  test.describe(`axe, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of ALL_PAGES) {
      test(route.name, async ({ page }, testInfo) => {
        await openPage(page, route.path);
        await expectNoNewViolations(page, route.name, scheme, testInfo);
      });
    }
  });
}
