import AxeBuilder from "@axe-core/playwright";
import { Page, TestInfo, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

// WCAG 2.2 A/AA through axe-core.
//
// The WebUI does not pass yet. accessibility-baseline.json lists, per page (or state) and theme, the rules known
// to fail today, so a check fails on a rule that is new there and stays green on the known backlog. Fixing a rule
// makes its baseline entry stale (reported as an annotation); drop it with
//   npm run test:e2e:baseline
// which rewrites the file from the current results - review its diff before committing, since it also records
// anything that has regressed.
export const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const BASELINE_FILE = path.join(__dirname, "..", "accessibility-baseline.json");
export const UPDATE_BASELINE = !!process.env["E2E_UPDATE_BASELINE"];

type Baseline = Record<string, Record<string, string[]>>; // page or state -> theme -> rule ids

function readBaseline(): Baseline {
  return fs.existsSync(BASELINE_FILE) ? (JSON.parse(fs.readFileSync(BASELINE_FILE, "utf8")) as Baseline) : {};
}

// Workers record their results side by side, so the read-modify-write of the one file is done under a lock: a directory
// that only one worker can create at a time. A lock older than LOCK_STALE_MS belongs to a run that was killed and is
// taken over.
const LOCK_STALE_MS = 30_000;

function writeBaseline(name: string, theme: string, rules: string[]): void {
  const lock = BASELINE_FILE + ".lock";
  for (;;) {
    try {
      fs.mkdirSync(lock);
      break;
    } catch {
      try {
        if (Date.now() - fs.statSync(lock).mtimeMs > LOCK_STALE_MS) fs.rmdirSync(lock);
      } catch {
        // The holder released it in the meantime.
      }
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 25);
    }
  }
  try {
    const baseline = readBaseline();
    baseline[name] = { ...baseline[name], [theme]: rules };
    const sorted = Object.fromEntries(Object.entries(baseline).sort(([a], [b]) => a.localeCompare(b)));
    fs.writeFileSync(BASELINE_FILE, JSON.stringify(sorted, null, 2) + "\n");
  } finally {
    fs.rmdirSync(lock);
  }
}

// Runs axe on the page as it is now and fails on any rule the baseline does not list for `name` and `scheme`.
export async function expectNoNewViolations(
  page: Page,
  name: string,
  scheme: string,
  testInfo: TestInfo,
  options: { include?: string } = {}
): Promise<void> {
  // Left out: Material's off-screen live region for snackbar announcements (aria-hidden by design, it comes and goes
  // with a toast; the toast itself stays in), and the corner ribbon an instance in debug mode wears (a rotated band
  // clipped to the corner of the screen, so it is "partially obscured" by construction).
  const builder = new AxeBuilder({ page })
    .withTags(WCAG_TAGS)
    .exclude("[id^='mat-snack-bar-container-live']")
    .exclude(".debug-ribbon");
  const results = await (options.include ? builder.include(options.include) : builder).analyze();
  // An analysis that checked nothing would pass as well.
  expect(results.passes.length).toBeGreaterThan(0);

  const found = [...new Set(results.violations.map((v) => v.id))].sort();
  if (UPDATE_BASELINE) {
    writeBaseline(name, scheme, found);
    return;
  }

  const known = readBaseline()[name]?.[scheme] ?? [];
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
}
