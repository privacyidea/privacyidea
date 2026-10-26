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
// palette and promises nothing, so only the edges it shades itself are checked.
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
const EDGE_MIX = 0.65;
// The contrast the grey each level shades its edges toward (--status-edge-tone) holds against the page.
const TONE_CONTRAST: Record<string, number> = { aaa: 7, aa: 4.5, a: 4.5 };

interface Level {
  ink: Rgb;
  // The grey the edges are shaded toward: dark on a light page, light on a dark one.
  tones: { light: Rgb; dark: Rgb };
  fills: Record<string, Rgb>;
  // The edges a level names itself; every other fill's edge is the fill shaded toward the tone.
  edges: Partial<Record<string, Rgb>>;
}

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

function parseTones(text: string): { light: Rgb; dark: Rgb } {
  const pair = /^light-dark\(\s*(hsl\([^)]*\)),\s*(hsl\([^)]*\))\s*\)$/.exec(text);
  if (!pair) throw new Error(`Unsupported edge tone in $status-colors: ${text}`);
  return { light: parseColor(pair[1]), dark: parseColor(pair[2]) };
}

function levels(): Record<string, Level> {
  const map = SOURCE.slice(SOURCE.indexOf("$status-colors: ("), SOURCE.indexOf("@mixin status-colors"));
  const result: Record<string, Level> = {};
  for (const level of ["aaa", "aa", "a"]) {
    const block = new RegExp(`"${level}": \\(([\\s\\S]*?)\\n  \\)`).exec(map)?.[1] ?? "";
    const value = (key: string) => new RegExp(`"${key}":\\s*(.+?),?\\s*$`, "m").exec(block)?.[1].trim() ?? "";
    result[level] = {
      ink: parseColor(value("ink")),
      tones: parseTones(value("edge-tone")),
      fills: Object.fromEntries(FILLS.map((fill) => [fill, parseColor(value(fill))])),
      edges: Object.fromEntries(
        FILLS.filter((fill) => value(`${fill}-edge`)).map((fill) => [fill, parseColor(value(`${fill}-edge`))])
      )
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

  // Only AAA promises the spacing. AA promises the 4.5:1 contrast, which WCAG AA asks for, and the status chips carry
  // text and icons besides colour.
  it.each([["aaa", 1.15]])(
    "level %s spaces the fills in lightness, so they stay apart without relying on hue",
    (level, trioMinimum) => {
      const fills = all[level].fills;
      const ratio = (a: string, b: string) => contrast(fills[a], fills[b]);
      for (let i = 0; i < FILLS.length; i++) {
        for (let j = i + 1; j < FILLS.length; j++) {
          expect({ pair: [FILLS[i], FILLS[j]], ok: ratio(FILLS[i], FILLS[j]) >= 1.15 }).toEqual({
            pair: [FILLS[i], FILLS[j]],
            ok: true
          });
        }
      }
      // The pairs red-green colour blindness confuses.
      for (const [a, b] of [
        ["green", "yellow"],
        ["green", "red"],
        ["yellow", "red"]
      ]) {
        expect({ pair: [a, b], ok: ratio(a, b) >= trioMinimum }).toEqual({ pair: [a, b], ok: true });
      }
    }
  );

  it.each(["aaa", "aa", "a"])("level %s has an edge that holds 3:1 against the page in both themes", (level) => {
    for (const fill of FILLS.filter((name) => !all[level].edges[name])) {
      const light = edge(all[level].fills[fill], all[level].tones.light);
      const dark = edge(all[level].fills[fill], all[level].tones.dark);
      for (const surface of LIGHT_SURFACES) {
        expect({ fill, theme: "light", ok: contrast(light, surface) >= 3 }).toEqual({ fill, theme: "light", ok: true });
      }
      for (const surface of DARK_SURFACES) {
        expect({ fill, theme: "dark", ok: contrast(dark, surface) >= 3 }).toEqual({ fill, theme: "dark", ok: true });
      }
    }
  });

  it.each(["aaa", "aa", "a"])(
    "level %s shades the edges toward a grey that holds its contrast against the page",
    (level) => {
      const minimum = TONE_CONTRAST[level];
      for (const surface of LIGHT_SURFACES) {
        expect({ surface, ok: contrast(all[level].tones.light, surface) >= minimum }).toEqual({ surface, ok: true });
      }
      for (const surface of DARK_SURFACES) {
        expect({ surface, ok: contrast(all[level].tones.dark, surface) >= minimum }).toEqual({ surface, ok: true });
      }
    }
  );

  it("lets only level A name its own edges, and keeps them lighter than their fills", () => {
    expect(Object.keys(all["aaa"].edges)).toEqual([]);
    expect(Object.keys(all["aa"].edges)).toEqual([]);
    expect(Object.keys(all["a"].edges)).toEqual(["green", "yellow", "red"]);
    for (const [fill, color] of Object.entries(all["a"].edges)) {
      expect({ fill, ok: contrast(color!, all["a"].fills[fill]) >= 1.5 }).toEqual({ fill, ok: true });
      expect({ fill, lighter: luminance(color!) > luminance(all["a"].fills[fill]) }).toEqual({ fill, lighter: true });
    }
  });

  it("reads every fill of every level", () => {
    for (const level of ["aaa", "aa", "a"]) {
      expect(Object.keys(all[level].fills)).toEqual(FILLS);
    }
    expect(all["aa"].fills["blue"]).toEqual([22, 83, 111]);
  });
});
