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

import { Component, input, linkedSignal, WritableSignal, output, viewChildren, ElementRef } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";

@Component({
  selector: "app-selector-buttons",
  standalone: true,
  imports: [MatButtonModule],
  templateUrl: "./selector-buttons.component.html",
  styleUrl: "./selector-buttons.component.scss"
})
export class SelectorButtonsComponent<T> {
  // Inputs
  readonly initialValue = input.required<T | null>();
  readonly values = input.required<T[]>();
  readonly labels = input<T[] | undefined>(undefined);
  readonly allowDeselect = input<boolean>(false);
  readonly disabled = input<boolean>(false);

  // Outputs
  readonly onSelect = output<T | null>();

  // Component State
  selectedValue: WritableSignal<T | null> = linkedSignal({
    source: () => this.initialValue(),
    computation: (source) => source
  });

  buttons = viewChildren<ElementRef<HTMLButtonElement>>("btn");

  // Public Methods
  selectValue(value: T): void {
    if (this.disabled()) {
      return;
    }

    if (this.selectedValue() === value) {
      if (this.allowDeselect()) {
        this.selectedValue.set(null);
        this.onSelect.emit(null);
      }
      return;
    }
    this.selectedValue.set(value);
    this.onSelect.emit(value);
  }

  public focusFirst(): void {
    const firstButton = this.buttons()[0]?.nativeElement;
    if (firstButton) {
      firstButton.focus();
    }
  }
}
