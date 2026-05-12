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

import { Component, EventEmitter, OnDestroy, OnInit, Output, ViewChild } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import {
  MatExpansionPanel,
  MatExpansionPanelDescription,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatIcon } from "@angular/material/icon";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTooltip } from "@angular/material/tooltip";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { EMPTY_PERIODIC_TASK } from "@services/periodic-task/periodic-task.service";
import { deepCopy } from "@utils/deep-copy.utils";
import { firstValueFrom } from "rxjs";
import { PeriodicTaskEditComponent } from "./periodic-task-edit/periodic-task-edit.component";
import { PeriodicTaskPanelComponent } from "./periodic-task-panel.component";

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
export class PeriodicTaskPanelNewComponent extends PeriodicTaskPanelComponent implements OnInit, OnDestroy {
  @ViewChild("panel") panel!: MatExpansionPanel;
  @Output() taskSaved = new EventEmitter<void>();

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(() => this.isEdited());
    this.pendingChangesService.registerValidChanges(() => this.canSave);
    this.pendingChangesService.registerSave(() => this.savePeriodicTask());
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

  override isEdited(): boolean {
    const editTask = this.editComponent?.editTask();
    if (!editTask) return false;
    return JSON.stringify(editTask) !== JSON.stringify(EMPTY_PERIODIC_TASK);
  }

  override cancelEdit(): void {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
      this.editComponent?.editTask.set(deepCopy(EMPTY_PERIODIC_TASK));
      this.editComponent?.resetFormState();
      this.panel.close();
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
            this.editComponent?.editTask.set(deepCopy(EMPTY_PERIODIC_TASK));
            this.editComponent?.resetFormState();
            this.panel.close();
          }
        }
      });
  }

  override async savePeriodicTask(): Promise<boolean> {
    const editedTask = this.editComponent?.editTask();
    if (!editedTask || !this.canSave) return false;
    try {
      const response = await firstValueFrom(this.periodicTaskService.savePeriodicTask(editedTask));
      if (response?.result?.value !== undefined) {
        this.isEditMode.set(false);
        this.periodicTaskService.periodicTasksResource.reload();
        this.panel.close();
        this.taskSaved.emit();
        this.editComponent?.editTask.set(deepCopy(EMPTY_PERIODIC_TASK));
        this.editComponent?.resetFormState();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }
}
