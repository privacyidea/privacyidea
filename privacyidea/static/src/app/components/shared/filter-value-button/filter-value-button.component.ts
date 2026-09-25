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
import { Component, computed, input, output } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { filterValueTooltip } from "@utils/filter-tooltip.utils";

/**
 * A small inline "filter by this value" button to place next to a cell value. It is deliberately dumb: it emits the
 * value on click and the host decides what to filter. Visibility can be driven by a parent via the inherited
 * `--filter-button-opacity` custom property (e.g. to reveal it only on row hover/focus).
 *
 * Without a value the whole element is hidden, so a spacing class set on it leaves no gap behind and a cell needs no
 * guard of its own.
 */
@Component({
  selector: "app-filter-value-button",
  standalone: true,
  imports: [MatIcon],
  templateUrl: "./filter-value-button.component.html",
  styleUrl: "./filter-value-button.component.scss",
  host: { "[style.display]": "hasValue() ? null : 'none'" }
})
export class FilterValueButtonComponent {
  readonly value = input.required<string>();
  // The column the value comes from, which names what the button filters by.
  readonly column = input<string>("");
  readonly label = computed(() => filterValueTooltip(this.column()));
  readonly filterValue = output<string>();
  // Cell values reach this through untyped row objects, so null/undefined arrive despite the declared type.
  readonly hasValue = computed(() => String(this.value() ?? "").trim() !== "");

  emit(event: Event): void {
    // Stop the click from also triggering the surrounding row/link.
    event.stopPropagation();
    this.filterValue.emit(this.value());
  }
}
