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
import { Component, EventEmitter, Input, Output } from "@angular/core";
import { ReactiveFormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";

@Component({
  selector: "app-clearable-input",
  standalone: true,
  imports: [ReactiveFormsModule, MatIconModule, MatIconButton],
  templateUrl: "./clearable-input.component.html",
  styleUrl: "./clearable-input.component.scss"
})
export class ClearableInputComponent {
  @Output() onClick = new EventEmitter<void>();
  @Input() showClearButton: boolean = true;

  clearInput(): void {
    this.onClick.emit();
  }
}
