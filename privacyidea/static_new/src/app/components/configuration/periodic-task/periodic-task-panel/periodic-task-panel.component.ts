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
import { ChangeDetectorRef, Component, inject, input, signal, ViewChild } from "@angular/core";
import { MatExpansionModule, MatExpansionPanel, MatExpansionPanelTitle } from "@angular/material/expansion";
import {
  EMPTY_PERIODIC_TASK,
  PERIODIC_TASK_MODULE_MAPPING,
  PeriodicTask,
  PeriodicTaskModule,
  PeriodicTaskService
} from "../../../../services/periodic-task/periodic-task.service";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { FormsModule } from "@angular/forms";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { PeriodicTaskReadComponent } from "./periodic-task-read/periodic-task-read.component";
import { MatDialog } from "@angular/material/dialog";
import { AuthService } from "../../../../services/auth/auth.service";
import { PeriodicTaskEditComponent } from "./periodic-task-edit/periodic-task-edit.component";
import { MatTooltip } from "@angular/material/tooltip";

@Component({
  selector: "app-periodic-task-panel",
  standalone: true,
  templateUrl: "periodic-task-panel.component.html",
  imports: [
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionModule,
    MatSlideToggle,
    FormsModule,
    MatIcon,
    MatIconButton,
    PeriodicTaskReadComponent,
    PeriodicTaskEditComponent,
    MatTooltip
  ],
  styleUrls: ["periodic-task-panel.component.scss"]
})
export class PeriodicTaskPanelComponent {
  periodicTaskService = inject(PeriodicTaskService);
  authService = inject(AuthService);
  private readonly dialog: MatDialog = inject(MatDialog);
  task = input<PeriodicTask>(EMPTY_PERIODIC_TASK);
  isEditMode = signal(false);

  deleteTask(): void {
    this.periodicTaskService.deleteWithConfirmDialog(this.task(), this.dialog, () => this.periodicTaskService.periodicTasksResource.reload());
  }

  toggleActive(activate: boolean): void {
    if (!this.task()) {
      return;
    }
    this.task()!.active = activate;
    if (!this.isEditMode()) {
      if (activate) {
        this.periodicTaskService.enablePeriodicTask(this.task()!.id).then(r => {
        });
      } else {
        this.periodicTaskService.disablePeriodicTask(this.task()!.id).then(r => {
        });
      }
    }
  }

  cancelEdit(): void {
    this.isEditMode.set(false);
  }

  @ViewChild(PeriodicTaskEditComponent) editComponent?: PeriodicTaskEditComponent;

  canSave = false;

  savePeriodicTask(): void {
    // Get the edited task from the edit component
    const editedTask = this.editComponent?.editTask();
    console.log(editedTask);
    if (editedTask && this.canSave) {
      this.periodicTaskService.savePeriodicTask(editedTask).subscribe({
        next: (response) => {
          if (response?.result?.value !== undefined) {
            this.periodicTaskService.periodicTasksResource.reload();
            this.isEditMode.set(false);
          }
          console.log(this.editComponent?.editTask());
        }
      });
    }
  }

  getModuleLabel(module: string): string {
    return PERIODIC_TASK_MODULE_MAPPING[module as PeriodicTaskModule] ?? module;
  }
}
