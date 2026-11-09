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

import { Page } from "@playwright/test";

// A control a user cannot fully reach: part of it lies outside an ancestor that clips its overflow, or it covers the
// text next to it. Both hide content and actions of a row whose text is longer than its cell (#6275).
export interface ClipProblem {
  control: string;
  problem: string;
}

// Scans the page content for controls that are cut off by a clipping ancestor and for controls that overlap the text
// of their own cell. Ancestors that scroll (overflow auto or scroll) are no problem: the control is reachable there.
export async function clippedControls(page: Page): Promise<ClipProblem[]> {
  return page.evaluate(() => {
    const TOLERANCE = 1.5;
    const CONTROLS =
      "button, a[href], a[role='button'], [role='button'], input:not([type='hidden']), mat-select, [role='combobox']";
    const problems: { control: string; problem: string }[] = [];
    const root = document.querySelector("main, [role='main']") ?? document.body;

    const label = (e: Element): string => {
      const text = (e.getAttribute("aria-label") ?? e.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 30);
      const cls = String(e.getAttribute("class") ?? "").split(" ")[0];
      return `${e.tagName.toLowerCase()}${cls ? "." + cls : ""} "${text}"`;
    };
    const shown = (e: Element, r: DOMRect): boolean => {
      const s = getComputedStyle(e);
      return (
        r.width > 0 &&
        r.height > 0 &&
        s.visibility !== "hidden" &&
        !e.closest(".cdk-visually-hidden, .debug-ribbon, [inert]")
      );
    };
    // Per axis: overflow hidden or clip cuts content off, while auto and scroll let the user get to it. A control inside
    // a scrolling area is reachable on that axis however far the area lies outside the clipping ancestors above it.
    const cuts = (v: string) => v === "hidden" || v === "clip";
    const scrolls = (v: string) => v === "auto" || v === "scroll";

    for (const control of Array.from(root.querySelectorAll(CONTROLS))) {
      const r = control.getBoundingClientRect();
      if (!shown(control, r)) {
        continue;
      }
      let reachableX = false;
      let reachableY = false;
      for (let a = control.parentElement; a && a !== document.documentElement; a = a.parentElement) {
        const s = getComputedStyle(a);
        const c = a.getBoundingClientRect();
        const cutX = !reachableX && cuts(s.overflowX) && (r.left < c.left - TOLERANCE || r.right > c.right + TOLERANCE);
        const cutY = !reachableY && cuts(s.overflowY) && (r.top < c.top - TOLERANCE || r.bottom > c.bottom + TOLERANCE);
        if (c.width > 0 && (cutX || cutY)) {
          problems.push({ control: label(control), problem: `cut off by ${label(a)}` });
          break;
        }
        reachableX ||= scrolls(s.overflowX);
        reachableY ||= scrolls(s.overflowY);
      }
      // Covering the text of its cell.
      const cell = control.closest("td, th");
      if (!cell) {
        continue;
      }
      const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        // A form field's label sits inside the field, where its input is.
        if (
          !n.textContent?.trim() ||
          control.contains(n) ||
          n.parentElement?.closest("label, mat-label, .mdc-floating-label")
        ) {
          continue;
        }
        const range = document.createRange();
        range.selectNodeContents(n);
        for (const t of Array.from(range.getClientRects())) {
          const w = Math.min(t.right, r.right) - Math.max(t.left, r.left);
          const h = Math.min(t.bottom, r.bottom) - Math.max(t.top, r.top);
          if (w > 2 && h > 2) {
            problems.push({
              control: label(control),
              problem: `covers the text "${n.textContent.trim().slice(0, 30)}"`
            });
            break;
          }
        }
      }
    }
    return problems;
  });
}
