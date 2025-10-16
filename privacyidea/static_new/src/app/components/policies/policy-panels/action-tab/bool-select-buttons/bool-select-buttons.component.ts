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
import { Component, EventEmitter, input, Output, OnInit, linkedSignal, WritableSignal, Input } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";

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
  initialValue = input.required<any>();
  @Input() valueLeft: any = false;
  @Input() valueRight: any = true;
  @Input() labelLeft: string = $localize`False`;
  @Input() labelRight: string = $localize`True`;
  @Output() onSelect = new EventEmitter<boolean>();

  // 1. Initialize selectedValue with a placeholder or default boolean value
  // The actual value will be set in ngOnInit
  selectedValue: WritableSignal<any> = linkedSignal({
    source: () => this.initialValue(),
    computation: (source) => source
  });

  ngOnInit() {
    const parsedValue = this.initialValue();
    this.selectedValue.set(parsedValue);
  }

  onSelectChange(value: any): void {
    this.selectedValue.set(value);
    this.onSelect.emit(value);
  }
}
