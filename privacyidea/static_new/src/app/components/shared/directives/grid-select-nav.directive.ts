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
import {
  ApplicationRef,
  Directive,
  ElementRef,
  OnDestroy,
  OnInit,
  inject,
  input,
  numberAttribute
} from "@angular/core";
import { MatOption, MatSelect } from "@angular/material/select";

@Directive({
  selector: "mat-select[appGridSelectNav]",
  standalone: true
})
export class GridSelectNavDirective implements OnInit, OnDestroy {
  readonly appGridSelectColumns = input<number | null, unknown>(null, { transform: numberAttribute });

  private readonly select = inject(MatSelect);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly appRef = inject(ApplicationRef);
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
    if (
      event.key !== "ArrowLeft" &&
      event.key !== "ArrowRight" &&
      event.key !== "ArrowUp" &&
      event.key !== "ArrowDown"
    )
      return;

    const options = this.select.options.toArray();
    if (options.length === 0) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    const keyManager = this.select._keyManager;
    const current = keyManager.activeItemIndex;
    if (current === null || current < 0) {
      keyManager.setActiveItem(0);
      this.appRef.tick();
      return;
    }

    const columns = this.columnCount(options);
    const last = options.length - 1;
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

    if (target < 0 || target > last) return;
    keyManager.setActiveItem(target);
    this.appRef.tick();
  }

  private columnCount(options: MatOption[]): number {
    const configured = this.appGridSelectColumns();
    if (configured !== null && configured > 0) return configured;
    if (options.length < 2) return 1;
    const firstTop = options[0]._getHostElement().offsetTop;
    let columns = 1;
    for (let i = 1; i < options.length; i++) {
      if (options[i]._getHostElement().offsetTop !== firstTop) break;
      columns++;
    }
    return columns;
  }
}
