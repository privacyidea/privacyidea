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
 *   - `more-below`: there is still content below the visible area.
 *
 * Two zero-height sentinels are inserted at the top and bottom of the scroll content and
 * observed via IntersectionObserver against the host as the scroll root, e.g.:
 *
 *   <div class="table-scroll-region" appScrollEdges>...</div>
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
  private topSentinel?: HTMLElement;
  private bottomSentinel?: HTMLElement;

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

    this.topObserver = new IntersectionObserver(
      ([entry]) => {
        // Top sentinel out of view → content has been scrolled down from the top.
        if (entry.isIntersecting) {
          this.renderer.removeClass(root, "scrolled-from-top");
        } else {
          this.renderer.addClass(root, "scrolled-from-top");
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

  ngOnDestroy(): void {
    this.topObserver?.disconnect();
    this.bottomObserver?.disconnect();
    if (this.topSentinel) {
      this.renderer.removeChild(this.renderer.parentNode(this.topSentinel), this.topSentinel);
    }
    if (this.bottomSentinel) {
      this.renderer.removeChild(this.renderer.parentNode(this.bottomSentinel), this.bottomSentinel);
    }
  }
}
