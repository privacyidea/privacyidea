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
import { Component, input, output } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";

/**
 * A small inline "filter by this value" button to place next to a cell value. It is deliberately dumb: it emits the
 * value on click and the host decides what to filter. Visibility can be driven by a parent via the inherited
 * `--filter-button-opacity` custom property (e.g. to reveal it only on row hover/focus).
 */
@Component({
  selector: "app-filter-value-button",
  standalone: true,
  imports: [MatIcon, MatTooltip],
  templateUrl: "./filter-value-button.component.html",
  styleUrl: "./filter-value-button.component.scss"
})
export class FilterValueButtonComponent {
  readonly value = input.required<string>();
  // Full tooltip text. Kept as a complete sentence (not noun-interpolated) so per-column variants can later be
  // supplied as independently-translatable $localize messages without breaking grammar in other languages.
  readonly label = input<string>($localize`Filter by this value`);
  readonly filterValue = output<string>();

  emit(event: Event): void {
    // Stop the click from also triggering the surrounding row/link.
    event.stopPropagation();
    this.filterValue.emit(this.value());
  }
}
