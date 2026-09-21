/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import * as fs from "fs";
import * as path from "path";

/**
 * Jest/jsdom does not run a layout engine, so it cannot evaluate media queries or measure
 * whether the toolbar actually overlaps the version text at a given viewport width. What this
 * suite CAN do is pin the exact values that were tuned by hand (in the browser, at the real
 * breakpoints) so nobody can silently drift them again without a failing test forcing them to
 * look at this file and update it deliberately. If a value below needs to change, verify the
 * toolbar in a real browser at the corresponding width first, then update the expectation here.
 */

const SCSS_PATH = path.resolve(__dirname, "navigation.component.scss");
const scss = fs.readFileSync(SCSS_PATH, "utf8");

/** Returns the `{ ... }` body of the first rule whose header contains `needle`, brace-matched
 * (not a naive non-greedy regex) so nested rules such as `&.node-shown` don't truncate it early. */
function ruleBody(source: string, needle: string, fromIndex = 0): string {
  const headerIndex = source.indexOf(needle, fromIndex);
  if (headerIndex === -1) {
    throw new Error(`Could not find rule "${needle}" in navigation.component.scss`);
  }
  const braceStart = source.indexOf("{", headerIndex);
  let depth = 0;
  let i = braceStart;
  for (; i < source.length; i++) {
    if (source[i] === "{") depth++;
    else if (source[i] === "}") {
      depth--;
      if (depth === 0) break;
    }
  }
  return source.slice(braceStart + 1, i);
}

/** `ruleBody` returns the raw text of a rule including any nested selectors (e.g.
 * `&.node-shown { ... }`), so a naive property search can accidentally match a declaration that
 * belongs to a nested rule instead of the rule itself. Declarations always precede nested
 * selectors in this file, so the text up to the first `{` is the rule's own top-level body. */
function ownDeclarations(body: string): string {
  const nestedStart = body.indexOf("{");
  return nestedStart === -1 ? body : body.slice(0, nestedStart);
}

function marginRight(body: string): number {
  const own = ownDeclarations(body);
  const explicit = own.match(/margin-right:\s*(\d+)px/);
  if (explicit) return Number(explicit[1]);

  // The base .version-text rule sets all four sides via the `margin` shorthand
  // (top right bottom left) instead of a dedicated margin-right.
  // `0` in a margin shorthand is valid without a unit, so each component's `px` is optional.
  const shorthand = own.match(/margin:\s*(\d+)(?:px)?\s+(\d+)(?:px)?\s+(\d+)(?:px)?\s+(\d+)(?:px)?/);
  if (shorthand) return Number(shorthand[2]);

  throw new Error(`Could not find margin-right in rule's own declarations: ${own}`);
}

function gap(body: string): number {
  const match = ownDeclarations(body).match(/gap:\s*(\d+)px/);
  if (!match) {
    throw new Error(`Could not find gap in rule's own declarations: ${body}`);
  }
  return Number(match[1]);
}

/** The compact breakpoint is a SCSS variable, not a literal, in the source (the 1600px one is a
 * literal) — read it out instead of hardcoding it a second time here, so a future rename of the
 * variable's value is what's under test rather than a copy of it. */
function compactBreakpointPx(): number {
  const match = scss.match(/\$breakpoint-compact:\s*(\d+)px/);
  if (!match) {
    throw new Error("Could not find $breakpoint-compact in navigation.component.scss");
  }
  return Number(match[1]);
}

const NARROW_BREAKPOINT_PX = 1600;

/** Bucket of the three `.version-text` rules that applies at a given effective (post-zoom) CSS
 * viewport width, mirroring the `max-width` cascade in the SCSS (last matching media query wins). */
type Bucket = "wide" | "compact" | "narrow";

function bucketFor(effectiveWidthPx: number, compactBreakpoint: number): Bucket {
  if (effectiveWidthPx <= NARROW_BREAKPOINT_PX) return "narrow";
  if (effectiveWidthPx <= compactBreakpoint) return "compact";
  return "wide";
}

/** Pinned margin-right values per bucket, as `{ base, nodeShown }`, kept in sync with the
 * individual pinning tests below. */
const EXPECTED_MARGINS: Record<Bucket, { base: number; nodeShown: number }> = {
  wide: { base: 34, nodeShown: 99 },
  compact: { base: 208, nodeShown: 272 },
  narrow: { base: 113, nodeShown: 113 }
};

/** Common laptop/external-monitor CSS viewport widths (at 100% zoom / 1x). Browser zoom does not
 * change the physical screen, it changes how many CSS px the layout viewport reports, so zooming
 * in on any of these is equivalent to laying out a narrower physical screen — that's the effective
 * width the media queries actually see. */
const REFERENCE_VIEWPORT_WIDTHS_PX = [1280, 1366, 1440, 1536, 1600, 1680, 1728, 1792, 1920, 2048, 2560];

/** Zoom levels a low-vision user is realistically going to reach for, per WCAG 1.4.4 (Resize
 * Text) which requires content and functionality to keep working up to 200% zoom. */
const ZOOM_LEVELS_PERCENT = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200];

describe("navigation toolbar layout (pinned SCSS values)", () => {
  it("keeps the secondary toolbar's item gap at 4px", () => {
    const body = ruleBody(scss, ".secondary-toolbar {");
    expect(gap(body)).toBe(4);
  });

  it("keeps the default .version-text margins", () => {
    const body = ruleBody(scss, ".version-text {");
    expect(body).toMatch(/margin:\s*0 34px 0 16px/);

    const nodeShown = ruleBody(body, "&.node-shown {");
    expect(marginRight(nodeShown)).toBe(99);
  });

  it("widens .version-text below the compact breakpoint ($breakpoint-compact = 1822px)", () => {
    const media = ruleBody(scss, "@media (max-width: $breakpoint-compact)");
    const versionText = ruleBody(media, ".version-text {");
    expect(marginRight(versionText)).toBe(208);

    const nodeShown = ruleBody(versionText, "&.node-shown {");
    expect(marginRight(nodeShown)).toBe(272);
  });

  it("narrows .version-text again below 1600px, where node name and version text no longer coexist", () => {
    const media = ruleBody(scss, "@media (max-width: 1600px)");
    const versionText = ruleBody(media, ".version-text {");
    expect(marginRight(versionText)).toBe(113);

    // Below 1600px the plain and node-shown margins converge: at that width the node name is
    // hidden already, so there is nothing left for the two states to differ over.
    const nodeShown = ruleBody(versionText, "&.node-shown {");
    expect(marginRight(nodeShown)).toBe(113);
  });

  it("keeps the narrow breakpoint strictly below the compact one", () => {
    // If these two ever cross, bucketFor()'s "last max-width wins" assumption -- and the
    // cascade in the SCSS itself, which relies on the narrower query appearing after the wider
    // one -- both silently stop matching what the browser actually renders.
    expect(NARROW_BREAKPOINT_PX).toBeLessThan(compactBreakpointPx());
  });

  describe("WCAG 1.4.4 zoom coverage (100%-200%, common viewport widths)", () => {
    const cases = REFERENCE_VIEWPORT_WIDTHS_PX.flatMap((viewportWidth) =>
      ZOOM_LEVELS_PERCENT.map((zoom) => ({
        viewportWidth,
        zoom,
        effectiveWidth: Math.round(viewportWidth / (zoom / 100))
      }))
    );

    it("builds a non-empty zoom x viewport matrix", () => {
      // Guards the test.each below against a silently-empty matrix (e.g. a typo turning
      // REFERENCE_VIEWPORT_WIDTHS_PX or ZOOM_LEVELS_PERCENT into `[]`), which would otherwise
      // report as "0 tests, all green" instead of failing.
      expect(cases.length).toBe(REFERENCE_VIEWPORT_WIDTHS_PX.length * ZOOM_LEVELS_PERCENT.length);
    });

    test.each(cases)(
      "$viewportWidth px @ $zoom% zoom (effective $effectiveWidth px) resolves to a pinned bucket",
      ({ effectiveWidth }) => {
        const compactBreakpoint = compactBreakpointPx();
        const bucket = bucketFor(effectiveWidth, compactBreakpoint);
        const expected = EXPECTED_MARGINS[bucket];

        const media =
          bucket === "narrow"
            ? ruleBody(scss, `@media (max-width: ${NARROW_BREAKPOINT_PX}px)`)
            : bucket === "compact"
              ? ruleBody(scss, "@media (max-width: $breakpoint-compact)")
              : scss;
        const versionText = ruleBody(media, ".version-text {");
        const nodeShown = ruleBody(versionText, "&.node-shown {");

        expect(marginRight(versionText)).toBe(expected.base);
        expect(marginRight(nodeShown)).toBe(expected.nodeShown);
      }
    );
  });
});
