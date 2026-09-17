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

import { Component, computed, DestroyRef, ElementRef, inject, input, output, signal, viewChild } from "@angular/core";

import { MatButtonModule } from "@angular/material/button";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { MatTooltipModule } from "@angular/material/tooltip";

@Component({
  selector: "app-multi-select-only",
  standalone: true,
  imports: [MatFormFieldModule, MatSelectModule, MatButtonModule, MatTooltipModule, MatIconModule],
  templateUrl: "./multi-select-only.component.html",
  styleUrls: ["./multi-select-only.component.scss"]
})
export class MultiSelectOnlyComponent<T = string | number> {
  // Inputs
  readonly label = input<string>("");
  readonly items = input<T[] | Set<T> | T[] | undefined>([]);
  readonly selectedItems = input<T[]>([]);
  readonly tooltipText = input<string>("");

  /** Maps an item onto the text shown for it. Defaults to the item itself. */
  readonly itemLabel = input<(item: T) => string>((item: T) => String(item));

  readonly subscriptSizing = input<"dynamic" | "fixed">("fixed");

  /** Width utility class applied to the form field (e.g. "input-width-xl"). Defaults to filling the host. */
  readonly fieldClass = input<string>("width-100");

  // Outputs
  readonly selectionChange = output<T[]>();

  /** Which control the keyboard marker sits on. Real focus never leaves the select. */
  readonly keyFocus = signal<"row" | "only" | "selectAll">("row");

  private readonly hostElement = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly select = viewChild.required(MatSelect);

  constructor() {
    const host = this.hostElement.nativeElement;
    const onKeydown = (event: KeyboardEvent) => this.handlePanelKeydown(event);
    // Capture phase: MatSelect keeps focus on its own host and handles keys there, so a bubbling
    // listener would only run after it has already closed the panel on Tab.
    host.addEventListener("keydown", onKeydown, true);
    inject(DestroyRef).onDestroy(() => host.removeEventListener("keydown", onKeydown, true));
  }

  /**
   * Localized labels for the toggle action.
   */
  protected readonly toggleLabels = {
    select: $localize`:@@common.selectAll:Select all`,
    deselect: $localize`:@@common.deselectAll:Deselect all`
  };

  /**
   * Normalizes input items to a unique array.
   */
  readonly uniqueItems = computed(() => {
    const source = this.items();
    const array = source instanceof Set ? Array.from(source) : source;
    return [...new Set(array)].sort();
  });

  /**
   * Disables the select if no items are available.
   */
  readonly isDisabled = computed(() => this.uniqueItems().length === 0);

  /**
   * Determines if all available unique items are currently selected.
   */
  readonly isAllSelected = computed(() => {
    const total = this.uniqueItems().length;
    return total > 0 && this.selectedItems().length === total;
  });

  /**
   * Pre-formats the string for the mat-select-trigger to keep the template clean.
   */
  readonly triggerValue = computed(() => {
    const label = this.itemLabel();
    return this.selectedItems()
      .map((item) => label(item))
      .join(", ");
  });

  /**
   * Standard selection handler.
   */
  public onSelectionChange(event: MatSelectChange): void {
    this.selectionChange.emit(event.value);
  }

  /**
   * Deselects everything and selects ONLY the targeted item.
   */
  public selectOnly(event: MouseEvent, item: T): void {
    event.stopPropagation();
    this.selectionChange.emit([item]);
  }

  /**
   * Drives the controls MatSelect's key manager cannot reach: Tab steps between the highlighted
   * row and its "Only" button, arrow up off the first row reaches the header. Real focus stays on
   * the select, mirroring how MatSelect highlights options without ever focusing them.
   */
  private handlePanelKeydown(event: KeyboardEvent): void {
    const select = this.select();
    if (!select.panelOpen) {
      return;
    }

    // Not queueMicrotask: the browser runs a microtask checkpoint after every listener, so that
    // would fire before MatSelect has even moved its highlight. rAF waits for the whole event.
    requestAnimationFrame(() => this.revealFirstOption());

    if (this.keyFocus() === "selectAll") {
      this.handleHeaderKeydown(event);
      return;
    }

    if (event.key === "Tab") {
      if (this.activeItem() === undefined) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      this.keyFocus.update((focus) => (focus === "only" ? "row" : "only"));
      return;
    }

    if (event.key === "ArrowUp" && this.keyFocus() === "row" && select.options.first?.active) {
      event.preventDefault();
      event.stopPropagation();
      this.enterHeader();
      return;
    }

    if (this.keyFocus() !== "only") {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      const item = this.activeItem();
      if (item === undefined) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      this.keyFocus.set("row");
      this.selectionChange.emit([item]);
      return;
    }

    // Anything else (arrows, Escape, typeahead) belongs to the row again.
    this.keyFocus.set("row");
  }

  private handleHeaderKeydown(event: KeyboardEvent): void {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      event.stopPropagation();
      this.toggleAll();
      return;
    }
    if (event.key === "ArrowUp") {
      // The header is the top of the panel; swallow it so the list does not steal the marker back.
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      event.stopPropagation();
      this.leaveHeader();
      return;
    }
    this.leaveHeader();
  }

  /**
   * Hands the key manager's highlight over to the header and back, so only one row ever looks
   * active. The manager's own index is left untouched, so arrow keys resume where they left off.
   */
  private enterHeader(): void {
    this.select().options.first?.setInactiveStyles();
    this.keyFocus.set("selectAll");
  }

  public leaveHeader(): void {
    if (this.keyFocus() === "selectAll") {
      this.select().options.first?.setActiveStyles();
    }
    this.keyFocus.set("row");
  }

  /**
   * MatSelect scrolls the highlighted option just far enough to be inside the panel, which for the
   * first one is the sticky header's height - so the header ends up covering it. Its own
   * `scrollTop = 0` shortcut is reserved for panels with option groups, so correct it here.
   */
  private revealFirstOption(): void {
    const select = this.select();
    if (select.panelOpen && select.options.first?.active) {
      select.panel.nativeElement.scrollTop = 0;
    }
  }

  /** The item behind the highlighted row. */
  private activeItem(): T | undefined {
    return this.select().options.find((option) => option.active)?.value as T | undefined;
  }

  /**
   * Toggles a single item.
   */
  public toggle(item: T): void {
    const currentSelection = this.selectedItems();
    const isSelected = currentSelection.includes(item);
    const newSelection = isSelected
      ? currentSelection.filter((i) => i !== item) // Remove item
      : [...currentSelection, item]; // Add item

    this.selectionChange.emit(newSelection);
  }

  /**
   * Toggles between selecting all and none.
   */
  public toggleAll(): void {
    this.selectionChange.emit(this.isAllSelected() ? [] : this.uniqueItems());
  }
}
