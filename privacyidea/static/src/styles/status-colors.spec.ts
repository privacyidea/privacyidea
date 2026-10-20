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

// The status colour levels promise a contrast, and a one-step tweak of a hue or lightness can quietly lose it: AAA
// holds 7:1 and AA 4.5:1 between the ink and every fill, and every fill's edge holds 3:1 against the page in both
// themes. This spec reads the $status-colors map in styles.scss and checks those numbers. Level A is the old WebUI
// palette and promises nothing, so only its edge is checked.
type Rgb = [number, number, number];

const SOURCE = readFileSync(resolve(__dirname, "styles.scss"), "utf8");
const FILLS = ["green", "blue", "yellow", "red", "grey"];
// Backgrounds of the page and its cards (theme.scss): light #e6e6e6 and white, dark 20% grey and a darker card.
const LIGHT_SURFACES: Rgb[] = [
  [230, 230, 230],
  [255, 255, 255]
];
const DARK_SURFACES: Rgb[] = [
  [51, 51, 51],
  [38, 38, 38]
];
// The share of the edge tone mixed into a fill (--green-edge and the others in styles.scss).
const EDGE_MIX = 0.55;

function parseColor(text: string): Rgb {
  const hex = /^#([0-9a-f]{6})$/i.exec(text);
  if (hex) {
    return [0, 2, 4].map((i) => parseInt(hex[1].slice(i, i + 2), 16)) as Rgb;
  }
  const hsl = /^hsl\(\s*([\d.]+),\s*([\d.]+)%,\s*([\d.]+)%\s*\)$/.exec(text);
  if (hsl) {
    const [h, s, l] = [Number(hsl[1]), Number(hsl[2]) / 100, Number(hsl[3]) / 100];
    const a = s * Math.min(l, 1 - l);
    const channel = (n: number) => {
      const k = (n + h / 30) % 12;
      return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))));
    };
    return [channel(0), channel(8), channel(4)];
  }
  if (text === "black") return [0, 0, 0];
  if (text === "white") return [255, 255, 255];
  throw new Error(`Unsupported colour in $status-colors: ${text}`);
}

function levels(): Record<string, { ink: Rgb; fills: Record<string, Rgb> }> {
  const map = SOURCE.slice(SOURCE.indexOf("$status-colors: ("), SOURCE.indexOf("@mixin status-colors"));
  const result: Record<string, { ink: Rgb; fills: Record<string, Rgb> }> = {};
  for (const level of ["aaa", "aa", "a"]) {
    const block = new RegExp(`"${level}": \\(([\\s\\S]*?)\\n  \\)`).exec(map)?.[1] ?? "";
    const value = (key: string) => new RegExp(`"${key}":\\s*(.+?),?\\s*$`, "m").exec(block)?.[1].trim() ?? "";
    result[level] = {
      ink: parseColor(value("ink")),
      fills: Object.fromEntries(FILLS.map((fill) => [fill, parseColor(value(fill))]))
    };
  }
  return result;
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

function edge(fill: Rgb, tone: Rgb): Rgb {
  return fill.map((c, i) => Math.round(c * (1 - EDGE_MIX) + tone[i] * EDGE_MIX)) as Rgb;
}

describe("status colors", () => {
  const all = levels();

  it.each([
    ["aaa", 7],
    ["aa", 4.5]
  ])("level %s holds %s:1 between the ink and every fill", (level, minimum) => {
    for (const fill of FILLS) {
      expect({ fill, ratio: contrast(all[level].ink, all[level].fills[fill]) >= minimum }).toEqual({
        fill,
        ratio: true
      });
    }
  });

  it.each(["aaa", "aa", "a"])("level %s has an edge that holds 3:1 against the page in both themes", (level) => {
    for (const fill of FILLS) {
      const light = edge(all[level].fills[fill], [0, 0, 0]);
      const dark = edge(all[level].fills[fill], [255, 255, 255]);
      for (const surface of LIGHT_SURFACES) {
        expect({ fill, theme: "light", ok: contrast(light, surface) >= 3 }).toEqual({ fill, theme: "light", ok: true });
      }
      for (const surface of DARK_SURFACES) {
        expect({ fill, theme: "dark", ok: contrast(dark, surface) >= 3 }).toEqual({ fill, theme: "dark", ok: true });
      }
    }
  });

  it("reads every fill of every level", () => {
    for (const level of ["aaa", "aa", "a"]) {
      expect(Object.keys(all[level].fills)).toEqual(FILLS);
    }
    expect(all["aa"].fills["blue"]).toEqual([22, 83, 111]);
  });
});
