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

  // .profile-hidden is applied from the template (navigation.component.html), driven by
  // NavigationComponent's ViewChild read of UserUtilsPanelComponent.isLargeScreen() — not by a
  // media query of its own. That's what keeps this margin's switch exactly in step with the
  // username/realm text disappearing: both react to the very same signal, so there is no second,
  // independently-tuned width for the two to drift apart at. See
  // navigation.component.spec.ts for the behavioral test of that class binding.
  it("narrows .version-text once .profile-hidden is applied", () => {
    const versionText = ruleBody(scss, ".version-text {");
    const profileHidden = ruleBody(versionText, "&.profile-hidden {");
    expect(profileHidden).toMatch(/\.version-prefix\s*\{\s*display:\s*none;/);
    expect(marginRight(profileHidden)).toBe(113);

    // The plain and node-shown margins converge here: at this width the node name sits in the
    // same now-hidden profile-text block, so there is nothing left for the two states to differ
    // over.
    const nodeShown = ruleBody(profileHidden, "&.node-shown {");
    expect(marginRight(nodeShown)).toBe(113);
  });

  // A plain width breakpoint, separate from .profile-hidden: the support/documentation buttons
  // drop their text at $breakpoint-compact well before the username/realm text disappears, and
  // .version-text takes up the slack they free up on the same row to stay visually balanced.
  it("widens .version-text below $breakpoint-compact, while the username/realm text is still visible", () => {
    const media = ruleBody(scss, "@media (max-width: $breakpoint-compact)");
    const versionText = ruleBody(media, ".version-text {");
    expect(marginRight(versionText)).toBe(208);

    const nodeShown = ruleBody(versionText, "&.node-shown {");
    expect(marginRight(nodeShown)).toBe(272);
  });

  it("keeps .profile-hidden's selector specificity above the $breakpoint-compact rule's, so it still wins once both apply", () => {
    // .version-text.profile-hidden (two classes) must outrank plain .version-text from the
    // media query above on specificity alone - source order can't be relied on here since the
    // class-based rule is written before the media query in this file.
    const versionText = ruleBody(scss, ".version-text {");
    expect(versionText).toMatch(/&\.profile-hidden\s*\{/);
  });
});
