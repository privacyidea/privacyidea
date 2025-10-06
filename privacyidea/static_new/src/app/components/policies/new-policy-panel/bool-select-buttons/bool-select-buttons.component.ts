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
import { Component, EventEmitter, Output, signal } from "@angular/core";

import { MatButtonModule } from "@angular/material/button";

@Component({
  selector: "app-bool-select-buttons",
  standalone: true,
  imports: [MatButtonModule],
  templateUrl: "./bool-select-buttons.component.html",
  styleUrl: "./bool-select-buttons.component.scss"
})
export class BoolSelectButtonsComponent {
  @Output() onSelect = new EventEmitter<boolean>();
  @Output() onSelectString = new EventEmitter<string>();
  @Output() onSelectNumber = new EventEmitter<Number>();
  selectedValue = signal<boolean>(true);

  ngOnInit() {
    this.selectBoolean(this.selectedValue());
  }

  selectBoolean(bool: boolean): void {
    this.selectedValue.set(bool);
    this.onSelect.emit(bool);
    this.onSelectString.emit(bool.toString());
    this.onSelectNumber.emit(bool ? 1 : 0);
  }
}
