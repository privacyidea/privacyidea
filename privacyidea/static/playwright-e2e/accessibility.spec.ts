import AxeBuilder from "@axe-core/playwright";
import * as fs from "fs";
import * as path from "path";
import { expect, test } from "./support/test";
import { ALL_PAGES } from "./support/routes";
import { openPage } from "./support/helpers";

// WCAG 2.2 A/AA through axe-core, on every page, in the light and the dark theme.
//
// The WebUI does not pass yet. accessibility-baseline.json lists, per page and theme, the rules known to fail
// today, so the suite fails on a rule that is new to a page and stays green on the known backlog. Fixing a
// rule makes its baseline entry stale (reported as an annotation); drop it with
//   E2E_UPDATE_BASELINE=1 npx playwright test --config playwright-e2e/playwright.config.ts accessibility --workers=1
// which rewrites the file from the current results - review its diff before committing, since it also
// records anything that has regressed.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const BASELINE_FILE = path.join(__dirname, "accessibility-baseline.json");
const UPDATE = !!process.env["E2E_UPDATE_BASELINE"];

type Baseline = Record<string, Record<string, string[]>>; // page -> theme -> rule ids

function readBaseline(): Baseline {
  return fs.existsSync(BASELINE_FILE) ? (JSON.parse(fs.readFileSync(BASELINE_FILE, "utf8")) as Baseline) : {};
}

function writeBaseline(page: string, theme: string, rules: string[]): void {
  const baseline = readBaseline();
  baseline[page] = { ...baseline[page], [theme]: rules };
  const sorted = Object.fromEntries(Object.entries(baseline).sort(([a], [b]) => a.localeCompare(b)));
  fs.writeFileSync(BASELINE_FILE, JSON.stringify(sorted, null, 2) + "\n");
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`axe, ${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of ALL_PAGES) {
      test(route.name, async ({ page }, testInfo) => {
        await openPage(page, route.path);
        const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
        // An analysis that checked nothing would pass as well.
        expect(results.passes.length).toBeGreaterThan(10);

        const found = [...new Set(results.violations.map((v) => v.id))].sort();
        if (UPDATE) {
          writeBaseline(route.name, scheme, found);
          return;
        }

        const known = readBaseline()[route.name]?.[scheme] ?? [];
        const fresh = results.violations.filter((v) => !known.includes(v.id));
        const report = fresh.map(
          (v) =>
            `${v.id} (${v.impact}): ${v.help}\n${v.nodes
              .slice(0, 8)
              .map((n) => "  " + n.target.join(" "))
              .join("\n")}`
        );
        for (const id of known.filter((id) => !found.includes(id))) {
          testInfo.annotations.push({ type: "stale baseline", description: `${id} no longer fails here` });
        }
        expect(report, report.join("\n")).toEqual([]);
      });
    }
  });
}
