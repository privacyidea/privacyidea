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
import { Directive, ElementRef, OnDestroy, OnInit, inject, input, numberAttribute } from "@angular/core";
import { MatSelect } from "@angular/material/select";

@Directive({
  selector: "mat-select[appGridSelectNav]",
  standalone: true
})
export class GridSelectNavDirective implements OnInit, OnDestroy {
  readonly appGridSelectColumns = input<number | null, unknown>(null, { transform: numberAttribute });

  private readonly select = inject(MatSelect);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly handler = (event: KeyboardEvent) => this.onKeydown(event);

  ngOnInit(): void {
    // MatSelect drives its options with an ActiveDescendantKeyManager, so DOM focus stays on the
    // mat-select host even while the overlay panel is open. Keydowns therefore target the host and
    // this capture listener sees them before MatSelect's own host `(keydown)` binding.
    this.host.nativeElement.addEventListener("keydown", this.handler, true);
  }

  ngOnDestroy(): void {
    this.host.nativeElement.removeEventListener("keydown", this.handler, true);
  }

  private onKeydown(event: KeyboardEvent): void {
    if (!this.select.panelOpen) return;
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight" && event.key !== "ArrowUp" && event.key !== "ArrowDown")
      return;

    const count = this.select.options.length;
    if (count === 0) return;

    const keyManager = this.select._keyManager;
    if (!keyManager) return;
    const current = keyManager.activeItemIndex;
    if (current === null || current < 0) {
      event.preventDefault();
      event.stopImmediatePropagation();
      keyManager.setActiveItem(0);
      return;
    }

    const columns = this.columnCount();
    let target = current;
    switch (event.key) {
      case "ArrowLeft":
        target = current - 1;
        break;
      case "ArrowRight":
        target = current + 1;
        break;
      case "ArrowUp":
        target = this.verticalTarget(current, columns, count, -1);
        break;
      case "ArrowDown":
        target = this.verticalTarget(current, columns, count, 1);
        break;
    }

    // Swallow the key even when the move leaves the grid, so MatSelect's key manager cannot fall
    // back to its single-option step. Moving off a horizontal edge does nothing.
    event.preventDefault();
    event.stopImmediatePropagation();
    if (target < 0 || target >= count) return;
    keyManager.setActiveItem(target);
  }

  /**
   * Moves one row within the same column. Running off the end of a column continues into the
   * neighbouring one, so holding ArrowDown walks down the first column, carries on at the top of the
   * next, and cycles back to the first column after the last one; ArrowUp travels the same circle
   * backwards. Empty cells of an incomplete last row are skipped.
   */
  private verticalTarget(current: number, columns: number, count: number, delta: number): number {
    const rows = Math.ceil(count / columns);
    const column = current % columns;
    const row = Math.floor(current / columns);

    const nextRow = row + delta;
    if (nextRow >= 0 && nextRow < rows) {
      const target = nextRow * columns + column;
      if (target < count) return target;
    }

    const nextColumn = (column + delta + columns) % columns;
    if (delta > 0) {
      const target = nextColumn;
      return target < count ? target : current;
    }
    for (let lastRow = rows - 1; lastRow >= 0; lastRow--) {
      const target = lastRow * columns + nextColumn;
      if (target < count) return target;
    }
    return current;
  }

  private columnCount(): number {
    const configured = this.appGridSelectColumns();
    if (configured !== null && configured > 0) return configured;
    const panel = this.select.panel?.nativeElement as HTMLElement | undefined;
    if (!panel) return 1;
    const optionEls = panel.querySelectorAll<HTMLElement>("mat-option");
    if (optionEls.length < 2) return 1;
    const firstTop = optionEls[0].offsetTop;
    let columns = 1;
    for (let i = 1; i < optionEls.length; i++) {
      if (optionEls[i].offsetTop !== firstTop) break;
      columns++;
    }
    return columns;
  }
}
