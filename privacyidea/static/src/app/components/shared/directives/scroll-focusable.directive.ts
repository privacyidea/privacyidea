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

import { AfterViewInit, Directive, ElementRef, inject, OnDestroy } from "@angular/core";

// A region that scrolls must be reachable with the keyboard, or a keyboard user cannot read what is cut off. The
// element takes part in the tab order only while it can scroll (its overflow is auto or scroll) and its content
// overflows it, so a cell whose list fits, or whose overflow is clipped or visible, adds no tab stop.
@Directive({
  selector: "[appScrollFocusable]",
  standalone: true
})
export class ScrollFocusableDirective implements AfterViewInit, OnDestroy {
  private readonly host: HTMLElement = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private resizeObserver?: ResizeObserver;

  ngAfterViewInit(): void {
    this.update();
    this.resizeObserver = new ResizeObserver(() => this.update());
    this.resizeObserver.observe(this.host);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
  }

  private update(): void {
    const style = getComputedStyle(this.host);
    const scrollsX = /auto|scroll/.test(style.overflowX) && this.host.scrollWidth > this.host.clientWidth + 1;
    const scrollsY = /auto|scroll/.test(style.overflowY) && this.host.scrollHeight > this.host.clientHeight + 1;
    if (scrollsX || scrollsY) {
      this.host.setAttribute("tabindex", "0");
    } else {
      this.host.removeAttribute("tabindex");
    }
  }
}
