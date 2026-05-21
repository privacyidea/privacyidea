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
import { Component, effect, inject, input, signal, ViewChild } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatExpansionModule, MatExpansionPanel, MatExpansionPanelTitle } from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTooltip } from "@angular/material/tooltip";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import {
  EMPTY_PERIODIC_TASK,
  PERIODIC_TASK_MODULE_MAPPING,
  PeriodicTask,
  PeriodicTaskModule,
  PeriodicTaskService
} from "@services/periodic-task/periodic-task.service";
import { firstValueFrom } from "rxjs";
import { PeriodicTaskEditComponent } from "./periodic-task-edit/periodic-task-edit.component";
import { PeriodicTaskReadComponent } from "./periodic-task-read/periodic-task-read.component";

@Component({
  selector: "app-periodic-task-panel",
  standalone: true,
  templateUrl: "periodic-task-panel.component.html",
  imports: [
    MatExpansionPanel,
    MatExpansionPanelTitle,
    MatExpansionModule,
    MatSlideToggle,
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
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly pendingChangesService = inject(PendingChangesService);
  task = input<PeriodicTask>(EMPTY_PERIODIC_TASK);
  isEditMode = signal(false);

  constructor() {
    effect(() => {
      if (this.isEditMode()) {
        this.pendingChangesService.registerHasChanges(() => this.isEditMode() && this.isEdited());
        this.pendingChangesService.registerValidChanges(() => this.canSave);
        this.pendingChangesService.registerSave(() => this.savePeriodicTask());
      }
    });
  }

  isEdited(): boolean {
    const editTask = this.editComponent?.editTask();
    if (!editTask) {
      return false;
    }
    return JSON.stringify(editTask) !== JSON.stringify(this.task());
  }

  async deleteTask(): Promise<void> {
    await this.periodicTaskService.deleteWithConfirmDialog(this.task());
    this.periodicTaskService.periodicTasksResource.reload();
  }

  toggleActive(activate: boolean): void {
    if (!this.task()) {
      return;
    }
    this.task()!.active = activate;
    if (!this.isEditMode()) {
      const taskId = this.task()!.id;
      if (taskId == null) {
        return;
      }
      if (activate) {
        this.periodicTaskService.enablePeriodicTask(taskId);
      } else {
        this.periodicTaskService.disablePeriodicTask(taskId);
      }
    }
  }

  cancelEdit(): void {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
      return;
    }
    this.dialogService
      .openDialog({
        component: SaveAndExitDialogComponent,
        data: {
          title: $localize`Discard changes`,
          allowSaveExit: this.canSave,
          saveExitDisabled: !this.canSave
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result === "save-exit") {
            if (!this.canSave) return;
            this.savePeriodicTask();
          } else if (result === "discard") {
            this.isEditMode.set(false);
          }
        }
      });
  }

  @ViewChild(PeriodicTaskEditComponent) editComponent?: PeriodicTaskEditComponent;

  canSave = false;

  async savePeriodicTask(): Promise<boolean> {
    const editedTask = this.editComponent?.editTask();
    if (!editedTask || !this.canSave) return false;
    try {
      const response = await firstValueFrom(this.periodicTaskService.savePeriodicTask(editedTask));
      if (response?.result?.value !== undefined) {
        this.periodicTaskService.periodicTasksResource.reload();
        this.isEditMode.set(false);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  getModuleLabel(module: string): string {
    return PERIODIC_TASK_MODULE_MAPPING[module as PeriodicTaskModule] ?? module;
  }
}
