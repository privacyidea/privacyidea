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

import { Component, EventEmitter, Output, ViewChild } from "@angular/core";
import { PeriodicTaskPanelComponent } from "./periodic-task-panel.component";
import {
  MatExpansionPanel,
  MatExpansionPanelDescription,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { PeriodicTaskEditComponent } from "./periodic-task-edit/periodic-task-edit.component";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { MatTooltip } from "@angular/material/tooltip";
import { EMPTY_PERIODIC_TASK } from "../../../../services/periodic-task/periodic-task.service";

@Component({
  selector: "app-periodic-task-panel-new",
  imports: [
    MatExpansionPanel,
    MatExpansionPanelDescription,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatIcon,
    MatIconButton,
    MatSlideToggle,
    PeriodicTaskEditComponent,
    MatTooltip
  ],
  templateUrl: "./periodic-task-panel-new.component.html",
  styleUrl: "./periodic-task-panel.component.scss"
})
export class PeriodicTaskPanelNewComponent extends PeriodicTaskPanelComponent {
  @ViewChild('panel') panel!: MatExpansionPanel;
  @Output() taskSaved = new EventEmitter<void>();

  override cancelEdit(): void {
    this.isEditMode.set(false);
    this.editComponent?.editTask.set(EMPTY_PERIODIC_TASK);
    this.panel.close();
  }

  override savePeriodicTask(): void {
    this.isEditMode.set(false);
    // Get the edited task from the edit component
    const editedTask = this.editComponent?.editTask();
    if (editedTask && this.canSave) {
      this.periodicTaskService.savePeriodicTask(editedTask).subscribe({
        next: (response) => {
          if (response?.result?.value !== undefined) {
            this.periodicTaskService.periodicTasksResource.reload();
            this.panel.close();
            this.taskSaved.emit();
            this.editComponent?.editTask.set(EMPTY_PERIODIC_TASK);
          }
        }
      });
    }
  }
}
