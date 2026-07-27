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
        target = current - columns;
        break;
      case "ArrowDown":
        target = current + columns;
        break;
    }

    if (target < 0 || target >= count) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    keyManager.setActiveItem(target);
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
