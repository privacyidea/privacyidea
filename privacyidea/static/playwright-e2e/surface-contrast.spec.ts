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

import { expect, Page } from "@playwright/test";
import { test } from "./support/test";
import { openPage } from "./support/helpers";

// A surface is a gradient between two tones: the card's tone tinted toward the shadow at one end and toward the
// highlight at the other (--surface-raised and --inset-surface-* in styles.scss). Labels and hints are written on it
// in --mat-sys-on-surface-variant, and have to keep 7:1 (WCAG 1.4.6, AAA) against the gradient's less favourable end
// at every depth level of the UI settings. axe audits 4.5:1 and cannot read a gradient, so this is measured here.

const THEMES = ["light", "dark"] as const;
const DEPTHS = ["flat", "subtle", "default", "strong", "very-strong"] as const;
const AAA = 7;

// The tone each surface is tinted from, by the name the card treatments know it under.
const SURFACES: Record<string, string> = {
  raised: "var(--table-color)",
  "group on a page": "var(--inset-tone-3)",
  "group in a group": "var(--inset-tone-5)",
  "deepest group": "var(--inset-tone-8)"
};

// The contrast of the label ink against the less favourable end of each surface, with <html> wearing `theme` and
// `depth` the way ThemeService and AppearanceService stamp them. The classes are put back afterwards and nothing is
// stored.
async function labelContrast(page: Page, theme: string, depth: string): Promise<Record<string, number>> {
  return page.evaluate(
    ({ theme, depth, surfaces }) => {
      const channel = (value: number) => {
        const v = value / 255;
        return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      };
      const luminance = ([r, g, b]: number[]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
      const contrast = (a: number[], b: number[]) => {
        const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
        return (high + 0.05) / (low + 0.05);
      };
      // A canvas turns whatever notation the browser computes a colour in (rgb(), color(srgb ...)) into bytes.
      const context = document.createElement("canvas").getContext("2d", { willReadFrequently: true })!;
      const probe = document.createElement("div");
      document.body.appendChild(probe);
      const resolve = (css: string): number[] => {
        probe.style.backgroundColor = css;
        context.clearRect(0, 0, 1, 1);
        context.fillStyle = getComputedStyle(probe).backgroundColor;
        context.fillRect(0, 0, 1, 1);
        return [...context.getImageData(0, 0, 1, 1).data.slice(0, 3)];
      };

      const root = document.documentElement;
      const worn = root.className;
      root.className = [...root.classList]
        .filter((c) => !["light", "dark", "system"].includes(c) && !c.startsWith("depth-"))
        .concat(theme, `depth-${depth}`)
        .join(" ");
      try {
        const ink = resolve("var(--mat-sys-on-surface-variant)");
        const result: Record<string, number> = {};
        for (const [name, tone] of Object.entries(surfaces)) {
          const ends = ["--mat-sys-shadow", "--mat-sys-light"].map((tint) =>
            resolve(`color-mix(in srgb, var(${tint}) var(--depth-tint), ${tone})`)
          );
          result[name] = Math.min(...ends.map((end) => contrast(end, ink)));
        }
        return result;
      } finally {
        root.className = worn;
        probe.remove();
      }
    },
    { theme, depth, surfaces: SURFACES }
  );
}

test.describe("label contrast on the surfaces", () => {
  for (const theme of THEMES) {
    test(`${theme} theme: a label keeps 7:1 on every surface at every depth level`, async ({ page }) => {
      // Any admin page carries the tokens; this one loads no data of its own.
      await openPage(page, "configuration/ui-settings");
      for (const depth of DEPTHS) {
        const measured = await labelContrast(page, theme, depth);
        for (const [surface, ratio] of Object.entries(measured)) {
          expect.soft(ratio, `depth ${depth}, ${surface}: label contrast`).toBeGreaterThanOrEqual(AAA);
        }
      }
    });
  }
});
