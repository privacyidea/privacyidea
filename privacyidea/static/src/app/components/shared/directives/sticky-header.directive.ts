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
import { AfterViewInit, Directive, ElementRef, inject, input, OnDestroy, Renderer2 } from "@angular/core";

/**
 * Toggles the `is-sticky` class on the host element once it sticks to the top of the given
 * scroll container. The scroll container is passed via the `appStickyHeader` input, typically
 * as a template reference to the scrollable element, e.g.:
 *
 *   <div #scrollContainer class="...">
 *     <div class="sticky-header" [appStickyHeader]="scrollContainer">...</div>
 *   </div>
 *
 * A zero-height sentinel is inserted right before the host and observed via an IntersectionObserver.
 */
@Directive({
  selector: "[appStickyHeader]",
  standalone: true
})
export class StickyHeaderDirective implements AfterViewInit, OnDestroy {
  readonly scrollRoot = input.required<HTMLElement>({ alias: "appStickyHeader" });

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly renderer = inject(Renderer2);
  private observer?: IntersectionObserver;
  private sentinel?: HTMLElement;

  ngAfterViewInit(): void {
    const root = this.scrollRoot();
    const headerElement = this.host.nativeElement;
    const parent = this.renderer.parentNode(headerElement);
    if (!root || !parent) return;

    const sentinel: HTMLElement = this.renderer.createElement("div");
    this.sentinel = sentinel;
    this.renderer.insertBefore(parent, sentinel, headerElement);

    this.observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.rootBounds) return;
        const isSticky = entry.boundingClientRect.top < entry.rootBounds.top;
        if (isSticky) {
          this.renderer.addClass(headerElement, "is-sticky");
        } else {
          this.renderer.removeClass(headerElement, "is-sticky");
        }
      },
      { root, threshold: [0, 1] }
    );
    this.observer.observe(sentinel);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    if (this.sentinel) {
      this.renderer.removeChild(this.renderer.parentNode(this.sentinel), this.sentinel);
    }
  }
}
