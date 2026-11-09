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

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// Every button-toggle group is painted from the one mat.button-toggle-overrides block in styles.scss. This spec reads
// that block, resolves its colours against the real light and dark themes in theme.scss, and checks that the text of a
// selected toggle holds AA (4.5:1) on its background, enabled and disabled alike. A disabled group still shows its
// selection, so Material's 12% / 38% on-surface defaults for it are replaced and must stay readable.
type Rgb = [number, number, number];

const STYLES = readFileSync(resolve(__dirname, "styles.scss"), "utf8");
const THEME = readFileSync(resolve(__dirname, "theme.scss"), "utf8");
const AA = 4.5;

function themeTokens(selector: string): Map<string, string> {
  const start = THEME.indexOf(`&.${selector} {`);
  const end = THEME.indexOf("\n  }\n", start);
  const tokens = new Map<string, string>();
  for (const match of THEME.slice(start, end).matchAll(/^\s*(--[\w-]+):\s*(.+?);\s*$/gm)) {
    tokens.set(match[1], match[2]);
  }
  return tokens;
}

function toggleToken(name: string): string {
  const block = STYLES.slice(STYLES.indexOf("@include mat.button-toggle-overrides("));
  const value = new RegExp(`^\\s*${name}:\\s*(.+?),?\\s*$`, "m").exec(block.slice(0, block.indexOf(");")))?.[1];
  if (!value) {
    throw new Error(`The button-toggle override ${name} is missing in styles.scss`);
  }
  return value.trim();
}

function parseColor(text: string): Rgb {
  const hsl = /^hsl\(\s*([\d.]+),\s*([\d.]+)%,\s*([\d.]+)%\s*\)$/.exec(text);
  if (!hsl) {
    throw new Error(`Unsupported colour in theme.scss: ${text}`);
  }
  const [h, s, l] = [Number(hsl[1]), Number(hsl[2]) / 100, Number(hsl[3]) / 100];
  const a = s * Math.min(l, 1 - l);
  const channel = (n: number) => {
    const k = (n + h / 30) % 12;
    return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))));
  };
  return [channel(0), channel(8), channel(4)];
}

// Follows custom-property references through the theme's declarations down to the colour, and mixes
// color-mix(in srgb, <colour> <share>%, <colour>) the way the browser does, channel by channel.
function resolveColor(value: string, tokens: Map<string, string>): Rgb {
  const mix = /^color-mix\(in srgb,\s*(var\(--[\w-]+\))\s+([\d.]+)%,\s*(var\(--[\w-]+\))\)$/.exec(value);
  if (mix) {
    const share = Number(mix[2]) / 100;
    const [first, second] = [resolveColor(mix[1], tokens), resolveColor(mix[3], tokens)];
    return first.map((channel, i) => Math.round(channel * share + second[i] * (1 - share))) as Rgb;
  }
  const reference = /^var\((--[\w-]+)\)$/.exec(value);
  if (!reference) {
    return parseColor(value);
  }
  const next = tokens.get(reference[1]);
  if (!next) {
    throw new Error(`${reference[1]} is not declared in the theme`);
  }
  return resolveColor(next, tokens);
}

function luminance([r, g, b]: Rgb): number {
  const [lr, lg, lb] = [r, g, b].map((c) => {
    const v = c / 255;
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
}

function contrast(a: Rgb, b: Rgb): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe("button toggle colors", () => {
  const pairs = [
    ["selected", "selected-state-background-color", "selected-state-text-color"],
    ["disabled and selected", "disabled-selected-state-background-color", "disabled-selected-state-text-color"]
  ];

  it.each(["light", "dark"])(
    "holds AA between the text and the background of a selected toggle in the %s theme",
    (theme) => {
      const tokens = themeTokens(theme);
      for (const [state, background, text] of pairs) {
        const ratio = contrast(resolveColor(toggleToken(text), tokens), resolveColor(toggleToken(background), tokens));
        expect({ state, ok: ratio >= AA }).toEqual({ state, ok: true });
      }
    }
  );

  it("paints a disabled selection differently from an enabled one", () => {
    for (const theme of ["light", "dark"]) {
      const tokens = themeTokens(theme);
      expect(resolveColor(toggleToken("disabled-selected-state-background-color"), tokens)).not.toEqual(
        resolveColor(toggleToken("selected-state-background-color"), tokens)
      );
    }
  });

  it("resolves the real theme colours", () => {
    const light = themeTokens("light");
    expect(resolveColor("var(--mat-sys-primary)", light)).toEqual(parseColor("hsl(199, 67%, 26%)"));
    expect(
      contrast(resolveColor("var(--mat-sys-on-primary)", light), resolveColor("var(--mat-sys-primary)", light))
    ).toBeGreaterThan(6);
    expect(resolveColor("var(--mat-sys-on-primary)", themeTokens("dark"))).toEqual(parseColor("hsl(198, 66%, 10%)"));
    expect(resolveColor("color-mix(in srgb, var(--mat-sys-primary) 50%, var(--mat-sys-on-primary))", light)).toEqual(
      resolveColor("var(--mat-sys-primary)", light).map((channel, i) =>
        Math.round((channel + resolveColor("var(--mat-sys-on-primary)", light)[i]) / 2)
      )
    );
  });

  it("rejects a token that is not set", () => {
    expect(() => toggleToken("no-such-token")).toThrow("no-such-token");
    expect(() => resolveColor("var(--mat-sys-primary)", new Map())).toThrow("not declared");
    expect(() => resolveColor("rebeccapurple", new Map())).toThrow("Unsupported");
  });
});
