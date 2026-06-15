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
import { AfterViewInit, Directive, ElementRef, inject, input, OnDestroy } from "@angular/core";

@Directive({
  selector: "[appMasonry]",
  standalone: true
})
export class MasonryDirective implements AfterViewInit, OnDestroy {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

  readonly columnWidthRem = input(45);

  private resizeObserver?: ResizeObserver;
  private mutationObserver?: MutationObserver;
  private frame = 0;

  ngAfterViewInit(): void {
    if (typeof ResizeObserver !== "undefined") {
      this.resizeObserver = new ResizeObserver(() => this.schedule());
      this.resizeObserver.observe(this.host);
      this.observeChildren();
    }
    if (typeof MutationObserver !== "undefined") {
      this.mutationObserver = new MutationObserver(() => {
        this.observeChildren();
        this.schedule();
      });
      this.mutationObserver.observe(this.host, { childList: true });
    }
    this.schedule();
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.mutationObserver?.disconnect();
    if (this.frame) {
      cancelAnimationFrame(this.frame);
    }
  }

  private observeChildren(): void {
    if (!this.resizeObserver) {
      return;
    }
    for (const child of Array.from(this.host.children)) {
      this.resizeObserver.observe(child);
    }
  }

  private schedule(): void {
    if (typeof requestAnimationFrame === "undefined") {
      this.layout();
      return;
    }
    cancelAnimationFrame(this.frame);
    this.frame = requestAnimationFrame(() => this.layout());
  }

  private layout(): void {
    const children = Array.from(this.host.children) as HTMLElement[];
    if (children.length === 0) {
      return;
    }
    const gap = parseFloat(getComputedStyle(this.host).getPropertyValue("--global-gap")) || 16;
    const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const minColumnWidth = this.columnWidthRem() * rootFontSize;
    const width = this.host.clientWidth;
    const columns = Math.max(1, Math.floor((width + gap) / (minColumnWidth + gap)));
    const columnWidth = (width - (columns - 1) * gap) / columns;
    const heights = new Array<number>(columns).fill(0);

    this.host.style.position = "relative";
    for (const child of children) {
      child.style.position = "absolute";
      child.style.boxSizing = "border-box";
      child.style.width = `${columnWidth}px`;
      let target = 0;
      for (let i = 1; i < columns; i++) {
        if (heights[i] < heights[target]) {
          target = i;
        }
      }
      child.style.left = `${target * (columnWidth + gap)}px`;
      child.style.top = `${heights[target]}px`;
      heights[target] += child.offsetHeight + gap;
    }
    this.host.style.height = `${Math.max(...heights)}px`;
  }
}
