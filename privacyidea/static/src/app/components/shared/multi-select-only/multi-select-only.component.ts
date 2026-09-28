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
  afterRenderEffect,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  input,
  output,
  signal,
  untracked,
  viewChild
} from "@angular/core";

import { LiveAnnouncer } from "@angular/cdk/a11y";
import { MatButtonModule } from "@angular/material/button";
import { MatOption } from "@angular/material/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIconModule } from "@angular/material/icon";
import { MatSelect, MatSelectChange, MatSelectModule } from "@angular/material/select";
import { MatTooltipModule } from "@angular/material/tooltip";

/** Keys that carry nothing but a modifier: they never move the highlight, so the marker stays put. */
const MODIFIER_ONLY_KEYS = new Set(["Alt", "Control", "Meta", "Shift"]);

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
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  private readonly select = viewChild.required(MatSelect);
  private scrollFrame = 0;

  constructor() {
    const host = this.hostElement.nativeElement;
    const onKeydown = (event: KeyboardEvent) => this.handlePanelKeydown(event);
    // Capture phase: MatSelect keeps focus on its own host and handles keys there, so a bubbling
    // listener would only run after it has already closed the panel on Tab.
    host.addEventListener("keydown", onKeydown, true);
    inject(DestroyRef).onDestroy(() => {
      host.removeEventListener("keydown", onKeydown, true);
      cancelAnimationFrame(this.scrollFrame);
    });

    // After render, not an effect: the highlight has to be restored once the new selection has
    // reached MatSelect, which happens while this component's own template bindings are updated.
    afterRenderEffect(() => {
      this.selectedItems();
      untracked(() => this.restoreHighlight());
    });
  }

  /**
   * Localized labels for the toggle action.
   */
  protected readonly toggleLabels = {
    select: $localize`:@@common.selectAll:Select all`,
    deselect: $localize`:@@common.deselectAll:Deselect all`
  };

  private readonly onlyLabel = $localize`:@@common.only:Only`;

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
    // A click on an option moves MatSelect's own highlight with it, so the marker cannot stay on
    // the header or on the button of the row the user has just left.
    this.resetMarker();
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
    if (!select.panelOpen || MODIFIER_ONLY_KEYS.has(event.key)) {
      return;
    }

    // The correction below has to see where MatSelect's own handler left the highlight, so it is
    // queued for after the event. Not queueMicrotask: the browser runs a microtask checkpoint
    // after every listener, which would come before MatSelect has even handled the key.
    const indexBefore = select._keyManager.activeItemIndex ?? -1;
    cancelAnimationFrame(this.scrollFrame);
    this.scrollFrame = requestAnimationFrame(() => this.revealFirstOption(indexBefore));

    if (this.keyFocus() === "selectAll") {
      this.handleHeaderKeydown(event);
      return;
    }

    if (event.key === "Tab") {
      this.handleTab(event);
      return;
    }

    if (event.key === "ArrowUp" && this.keyFocus() === "row" && select._keyManager.activeItemIndex === 0) {
      event.preventDefault();
      event.stopPropagation();
      this.enterHeader();
      return;
    }

    if (this.keyFocus() !== "only") {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      const option = this.activeOption();
      if (!option) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      this.keyFocus.set("row");
      this.selectionChange.emit([option.value as T]);
      return;
    }

    // Anything else (arrows, Escape, typeahead) belongs to the row again.
    this.keyFocus.set("row");
  }

  /**
   * Tab steps from the highlighted row onto its "Only" button, shift+Tab steps back off it.
   * Tabbing forward off the button is left to MatSelect, so the panel still closes and focus moves
   * on to the next control instead of the marker cycling between the two forever.
   */
  private handleTab(event: KeyboardEvent): void {
    if (this.keyFocus() === "only") {
      this.keyFocus.set("row");
      if (event.shiftKey) {
        event.preventDefault();
        event.stopPropagation();
        this.announceRow();
      }
      return;
    }

    const option = this.activeOption();
    if (event.shiftKey || !option) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    this.keyFocus.set("only");
    this.liveAnnouncer.announce(`${this.onlyLabel} ${this.itemLabel()(option.value as T)}`);
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
      this.resetMarker();
      this.announceRow();
      return;
    }
    this.resetMarker();
  }

  /**
   * Hands the key manager's highlight over to the header, so only one row ever looks active. The
   * manager's own index is left untouched, so arrow keys resume where they left off.
   */
  private enterHeader(): void {
    this.activeOption()?.setInactiveStyles();
    this.keyFocus.set("selectAll");
    this.liveAnnouncer.announce(this.isAllSelected() ? this.toggleLabels.deselect : this.toggleLabels.select);
  }

  /**
   * Puts the marker back on the highlighted row - whichever row the key manager points at by now,
   * since a click on an option moves it while the marker sits on the header.
   */
  public resetMarker(): void {
    if (this.keyFocus() === "selectAll") {
      this.activeOption()?.setActiveStyles();
    }
    this.keyFocus.set("row");
  }

  /**
   * The marker is not a focused element, so assistive technology reads the row MatSelect reports
   * as the active descendant - which stays on the row while the marker is on the header or on a
   * button. Announcing the move keeps what is read in step with what Enter will do.
   */
  private announceRow(): void {
    const option = this.activeOption();
    if (option) {
      this.liveAnnouncer.announce(this.itemLabel()(option.value as T));
    }
  }

  /**
   * MatSelect scrolls the highlighted option just far enough to be inside the panel, which for the
   * first one is the sticky header's height - so the header ends up covering it. Its own
   * `scrollTop = 0` shortcut is reserved for panels with option groups, so correct it here. Only a
   * key press that moved the highlight onto the first row may scroll: a panel the user scrolled by
   * hand has to stay where it is.
   */
  private revealFirstOption(previousIndex: number): void {
    const select = this.select();
    if (select.panelOpen && previousIndex !== 0 && select._keyManager.activeItemIndex === 0) {
      select.panel.nativeElement.scrollTop = 0;
    }
  }

  /**
   * Restores the highlight that writing a value clears: MatSelect resets every option's active
   * styles when a new selection is written into it, but leaves its key manager on the same row -
   * so without this the marker vanishes as soon as the parent writes an emitted selection back.
   */
  private restoreHighlight(): void {
    if (this.select().panelOpen && this.keyFocus() !== "selectAll") {
      this.activeOption()?.setActiveStyles();
    }
  }

  /** The row the key manager points at - the same one MatSelect reports as its active descendant. */
  private activeOption(): MatOption | null {
    return this.select()._keyManager?.activeItem ?? null;
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
