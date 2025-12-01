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


import { Component, EventEmitter, input, linkedSignal, Output, ViewEncapsulation } from "@angular/core";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { FormsModule } from "@angular/forms";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { PeriodicTaskOption } from "../../../../../../services/periodic-task/periodic-task.service";

@Component({
  selector: "app-periodic-task-option-detail",
  imports: [
    MatFormField,
    MatLabel,
    MatInput,
    FormsModule,
    MatButton,
    MatIcon
  ],
  templateUrl: "./periodic-task-option-detail.component.html",
  styleUrl: "./periodic-task-option-detail.component.scss",
  encapsulation: ViewEncapsulation.None
})
export class PeriodicTaskOptionDetailComponent {
  option = input({ name: "", type: "", description: "", value: "" } as PeriodicTaskOption);
  showAddButton = input(true);
  value = linkedSignal(() => this.option().value ?? "");

  @Output() newValue = new EventEmitter<string>();

  addOption(): void {
    if (!this.value()) {
      this.value.set("True");
    }
    this.newValue.emit(this.value());
  }
}
