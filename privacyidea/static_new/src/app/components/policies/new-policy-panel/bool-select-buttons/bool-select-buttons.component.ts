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
import { Component, EventEmitter, input, Output, OnInit, linkedSignal, WritableSignal } from "@angular/core";

import { MatButtonModule } from "@angular/material/button";
import { parseBooleanValue } from "../../../../utils/parse-boolean-value";

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
  @Output() onSelectNumber = new EventEmitter<Number>();
  @Output() onSelectString = new EventEmitter<string>();

  // 1. Initialize selectedValue with a placeholder or default boolean value
  // The actual value will be set in ngOnInit
  selectedValue: WritableSignal<boolean> = linkedSignal({
    source: () => this.initialValue(),
    computation: (source) => {
      return parseBooleanValue(source);
    }
  });

  ngOnInit() {
    const parsedValue = parseBooleanValue(this.initialValue());
    this.selectedValue.set(parsedValue);
  }

  selectBoolean(bool: boolean): void {
    this.selectedValue.set(bool);
    this.onSelect.emit(bool);
    this.onSelectString.emit(bool.toString());
    this.onSelectNumber.emit(bool ? 1 : 0);
  }
}