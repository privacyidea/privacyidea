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

  readonly columnWidthRem = input(40);

  // Maximum number of columns. When > 0 the layout uses up to this many columns
  // but never makes a column narrower than columnWidthRem, reducing the count as
  // the available width shrinks (e.g. under browser zoom) instead of overflowing.
  // 0 keeps the column count purely width-based.
  readonly columns = input(0);

  private resizeObserver?: ResizeObserver;
  private mutationObserver?: MutationObserver;
  private readonly observedChildren = new Set<HTMLElement>();
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
      this.mutationObserver.observe(this.host, { childList: true, subtree: true });
    }
    this.schedule();
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    this.mutationObserver?.disconnect();
    this.observedChildren.clear();
    if (this.frame) {
      cancelAnimationFrame(this.frame);
    }
  }

  private observeChildren(): void {
    if (!this.resizeObserver) {
      return;
    }
    const current = new Set(this.collectItems(this.host));
    for (const child of this.observedChildren) {
      if (!current.has(child)) {
        this.resizeObserver.unobserve(child);
        this.observedChildren.delete(child);
      }
    }
    for (const child of current) {
      if (!this.observedChildren.has(child)) {
        this.resizeObserver.observe(child);
        this.observedChildren.add(child);
      }
    }
  }

  private collectItems(parent: HTMLElement): HTMLElement[] {
    const items: HTMLElement[] = [];
    for (const child of Array.from(parent.children) as HTMLElement[]) {
      if (getComputedStyle(child).display === "contents") {
        items.push(...this.collectItems(child));
      } else {
        items.push(child);
      }
    }
    return items;
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
    const children = this.collectItems(this.host);
    if (children.length === 0) {
      return;
    }
    const gap = parseFloat(getComputedStyle(this.host).getPropertyValue("--global-gap")) || 16;
    const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const minColumnWidth = this.columnWidthRem() * rootFontSize;
    const width = this.host.clientWidth;
    // Columns that fit while keeping each at least minColumnWidth wide. A
    // requested fixed count is an upper bound: it never forces columns narrower
    // than minColumnWidth (which under browser zoom would make cards overlap),
    // so the layout drops to fewer columns instead.
    const fitColumns = Math.max(1, Math.floor((width + gap) / (minColumnWidth + gap)));
    const requestedColumns = this.columns();
    const columns = requestedColumns > 0 ? Math.min(requestedColumns, fitColumns) : fitColumns;
    const columnWidth = (width - (columns - 1) * gap) / columns;
    const heights = new Array<number>(columns).fill(0);

    this.host.style.position = "relative";
    for (const child of children) {
      child.style.position = "absolute";
      child.style.boxSizing = "border-box";
      child.style.width = `${columnWidth}px`;
    }

    const childHeights = children.map((child) => child.offsetHeight);

    children.forEach((child, index) => {
      let target = 0;
      for (let i = 1; i < columns; i++) {
        if (heights[i] < heights[target]) {
          target = i;
        }
      }
      child.style.left = `${target * (columnWidth + gap)}px`;
      child.style.top = `${heights[target]}px`;
      heights[target] += childHeights[index] + gap;
    });
    this.host.style.height = `${Math.max(...heights)}px`;
  }
}
