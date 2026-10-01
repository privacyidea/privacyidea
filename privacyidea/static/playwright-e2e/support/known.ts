import { TestType } from "@playwright/test";

// Failures the WebUI has today, by check. A listed test runs and is expected to fail (test.fail): it stays
// visible in every report, a new failure elsewhere still breaks the build, and once the page is fixed the
// test reports "expected to fail, but passed" - the cue to delete its entry here.
type Known = Record<string, { reason: string; pages: string[] | "all" }>;

export const KNOWN: Known = {
  "single main landmark": {
    reason: "every page renders two <main> landmarks",
    pages: "all"
  },
  "table accessible name": {
    reason: "the table has no aria-label, aria-labelledby or caption",
    pages: [
      "api clients",
      "ca connectors",
      "conditional access",
      "container templates",
      "events",
      "machines",
      "periodic tasks",
      "policies",
      "privacyidea servers",
      "radius servers",
      "service ids",
      "sms gateways",
      "smtp servers",
      "tokengroups"
    ]
  },
  "tier width": {
    reason: "the header's label and its sort/filter buttons are wider than the column's tier",
    pages: ["challenges", "containers", "container templates", "realms"]
  },
  "paginator total at 200%": {
    reason: "the row has no room for the total at 960 CSS px; the range shows alone",
    pages: [
      "api clients",
      "audit",
      "authentication log",
      "ca connectors",
      "challenges",
      "conditional access",
      "containers",
      "container templates",
      "events",
      "locked users",
      "machines",
      "privacyidea servers",
      "radius servers",
      "service ids",
      "sms gateways",
      "smtp servers",
      "tokengroups",
      "tokens",
      "users"
    ]
  },
  "focus indicator": {
    reason: "the overflow-more button (.overflow-more-btn) shows no focus indicator",
    pages: ["radius create", "sms create", "smtp create"]
  },
  "tab stops visible": {
    reason: "Tab lands on a link with no box (an empty cell link)",
    pages: ["audit", "challenges", "token applications"]
  }
};

// Marks the running test as an expected failure when the check is known to fail on this page.
export function knownFailure(test: Pick<TestType<any, any>, "fail">, check: string, page: string): void {
  const known = KNOWN[check];
  if (known && (known.pages === "all" || known.pages.includes(page))) {
    test.fail(true, known.reason);
  }
}
