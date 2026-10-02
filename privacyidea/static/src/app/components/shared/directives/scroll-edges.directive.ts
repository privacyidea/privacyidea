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
import { AfterViewInit, Directive, ElementRef, inject, OnDestroy, Renderer2 } from "@angular/core";

/**
 * Toggles edge classes on a scrollable host so callers can show a divider only when
 * there is hidden content in that direction:
 *
 *   - `scrolled-from-top`: the content is scrolled down from the very top.
 *   - `controls-collapsed`: scrolled from the top, with enough overflow that the page may collapse
 *     the controls above the host (an action row, a filter hint) without that undoing the scroll -
 *     see overflowOutlastsControlsAbove.
 *   - `more-below`: there is still content below the visible area.
 *
 * Two zero-height sentinels are inserted at the top and bottom of the scroll content and
 * observed via IntersectionObserver against the host as the scroll root, e.g.:
 *
 *   <div class="table-scroll-region" appScrollEdges>...</div>
 *
 * It also tracks the size of a sticky `.mat-mdc-header-row`, if the host has one, as the
 * `--sticky-header-height` / `--sticky-header-width` custom properties on the host.
 * table-global.scss reads them to size a single `.sticky-header-shadow` layer spanning the row, so
 * the elevation under the sticky header is cast once rather than once per header cell (which seams
 * at every column boundary where two adjacent cells' shadows overlap). The width is tracked
 * explicitly rather than left at the host's own 100% - a narrow table (e.g. external-services,
 * col-width-* tiers well short of the row) sets its own table width to auto instead of 100% so its
 * columns do not stretch, and the shadow div is this host's flex child, not the table's, so it would
 * otherwise stretch to the full flex width regardless and cast past the table's real right edge.
 */
@Directive({
  selector: "[appScrollEdges]",
  standalone: true
})
export class ScrollEdgesDirective implements AfterViewInit, OnDestroy {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly renderer = inject(Renderer2);
  private topObserver?: IntersectionObserver;
  private bottomObserver?: IntersectionObserver;
  private headerResizeObserver?: ResizeObserver;
  private topSentinel?: HTMLElement;
  private bottomSentinel?: HTMLElement;
  private headerShadow?: HTMLElement;

  ngAfterViewInit(): void {
    const root = this.host.nativeElement;

    const topSentinel: HTMLElement = this.renderer.createElement("div");
    const bottomSentinel: HTMLElement = this.renderer.createElement("div");
    this.topSentinel = topSentinel;
    this.bottomSentinel = bottomSentinel;
    this.renderer.setStyle(topSentinel, "height", "0");
    this.renderer.setStyle(bottomSentinel, "height", "0");
    this.renderer.insertBefore(root, topSentinel, root.firstChild);
    this.renderer.appendChild(root, bottomSentinel);

    const headerRow = root.querySelector<HTMLElement>(".mat-mdc-header-row");
    if (headerRow) {
      const headerShadow: HTMLElement = this.renderer.createElement("div");
      this.headerShadow = headerShadow;
      this.renderer.addClass(headerShadow, "sticky-header-shadow");
      this.renderer.insertBefore(root, headerShadow, topSentinel.nextSibling);

      this.headerResizeObserver = new ResizeObserver(() => {
        root.style.setProperty("--sticky-header-height", `${headerRow.offsetHeight}px`);
        root.style.setProperty("--sticky-header-width", `${headerRow.offsetWidth}px`);
      });
      this.headerResizeObserver.observe(headerRow);
    }

    this.topObserver = new IntersectionObserver(
      ([entry]) => {
        // Top sentinel out of view → content has been scrolled down from the top.
        if (entry.isIntersecting) {
          this.renderer.removeClass(root, "scrolled-from-top");
          this.renderer.removeClass(root, "controls-collapsed");
        } else {
          this.renderer.addClass(root, "scrolled-from-top");
          if (this.overflowOutlastsControlsAbove(root)) {
            this.renderer.addClass(root, "controls-collapsed");
          }
        }
      },
      { root }
    );
    this.topObserver.observe(topSentinel);

    this.bottomObserver = new IntersectionObserver(
      ([entry]) => {
        // Bottom sentinel visible → the bottom edge has been reached.
        if (entry.isIntersecting) {
          this.renderer.removeClass(root, "more-below");
        } else {
          this.renderer.addClass(root, "more-below");
        }
      },
      { root }
    );
    this.bottomObserver.observe(bottomSentinel);
  }

  // Collapsing the controls above the host hands their height to the host. Content that overflows
  // by no more than that then fits: scrollTop clamps back to 0, the top sentinel comes back into view
  // and the controls expand again, undoing the scroll that collapsed them. So they only collapse when
  // the overflow outlasts what collapsing frees: every action row above the host (its height and
  // bottom margin) and every filter hint above it - see actions-row-collapse in table.scss and the
  // hint rule in table-global.scss for what collapses.
  private overflowOutlastsControlsAbove(root: HTMLElement): boolean {
    const parent = root.parentElement;
    if (!parent) {
      return false;
    }
    const above = (el: Element) => el.compareDocumentPosition(root) & Node.DOCUMENT_POSITION_FOLLOWING;
    let freed = 0;
    for (const row of Array.from(parent.querySelectorAll<HTMLElement>(ScrollEdgesDirective.COLLAPSING_ROWS))) {
      if (above(row)) {
        freed += row.getBoundingClientRect().height + (parseFloat(getComputedStyle(row).marginBottom) || 0);
      }
    }
    for (const hint of Array.from(parent.querySelectorAll(".filter-paginator-container mat-hint"))) {
      if (above(hint)) {
        freed += hint.getBoundingClientRect().height;
      }
    }
    return root.scrollHeight - root.clientHeight > freed;
  }

  // The action rows the table pages collapse on scroll (table.scss's actions-row-collapse).
  private static readonly COLLAPSING_ROWS = ".actions-row, .token-actions-row, .container-actions-row";

  ngOnDestroy(): void {
    this.topObserver?.disconnect();
    this.bottomObserver?.disconnect();
    this.headerResizeObserver?.disconnect();
    if (this.topSentinel) {
      this.renderer.removeChild(this.renderer.parentNode(this.topSentinel), this.topSentinel);
    }
    if (this.bottomSentinel) {
      this.renderer.removeChild(this.renderer.parentNode(this.bottomSentinel), this.bottomSentinel);
    }
    if (this.headerShadow) {
      this.renderer.removeChild(this.renderer.parentNode(this.headerShadow), this.headerShadow);
    }
  }
}
