/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, EventEmitter, input, Output, signal, OnInit, linkedSignal, WritableSignal } from "@angular/core";

import { MatButtonModule } from "@angular/material/button";
import { assert } from "../../../../utils/assert";

@Component({
  selector: "app-bool-select-buttons",
  standalone: true,
  imports: [MatButtonModule],
  templateUrl: "./bool-select-buttons.component.html",
  styleUrl: "./bool-select-buttons.component.scss"
})
// Implement OnInit to use the hook
export class BoolSelectButtonsComponent implements OnInit {
  // Input definition is correct
  initialValue = input.required<string | number | boolean>();

  @Output() onSelect = new EventEmitter<boolean>();
  @Output() onSelectString = new EventEmitter<string>();
  @Output() onSelectNumber = new EventEmitter<Number>();

  // 1. Initialize selectedValue with a placeholder or default boolean value
  // The actual value will be set in ngOnInit
  selectedValue: WritableSignal<boolean> = linkedSignal({
    source: () => this.initialValue(),
    computation: (source) => {
      return this._parseBoolean(source);
    }
  });

  ngOnInit() {
    const parsedValue = this._parseBoolean(this.initialValue());
    this.selectedValue.set(parsedValue);
  }

  _parseBoolean(initialValue: string | number | boolean): boolean {
    console.log("Parsing initialValue:", initialValue);
    const typeofInitialValue = typeof initialValue;
    if (typeofInitialValue === "boolean") {
      return !!initialValue;
    }
    if (typeofInitialValue === "number") {
      if (initialValue === 1) return true;
      if (initialValue === 0) return false;
      assert(false, `Initial value for BoolSelectButtonsComponent must be 0 or 1 if number, but was ${initialValue}`);
    }
    if (typeofInitialValue === "string") {
      if (String(initialValue).toLowerCase() === "true") return true;
      if (String(initialValue).toLowerCase() === "false") return false;
      assert(
        false,
        `Initial value for BoolSelectButtonsComponent must be "true" or "false" if string, but was ${initialValue}`
      );
    }
    assert(
      false,
      `Initial value for BoolSelectButtonsComponent must be boolean, 0, 1, "true" or "false", but was ${initialValue}`
    );
    return false;
  }

  selectBoolean(bool: boolean): void {
    this.selectedValue.set(bool);
    this.onSelect.emit(bool);
    this.onSelectString.emit(bool.toString());
    this.onSelectNumber.emit(bool ? 1 : 0);
  }
}
