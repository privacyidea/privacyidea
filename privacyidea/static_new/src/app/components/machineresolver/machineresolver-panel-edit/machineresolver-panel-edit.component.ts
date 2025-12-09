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

import { Component, computed, inject, input, linkedSignal, signal, WritableSignal } from "@angular/core";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import {
  Machineresolver,
  MachineresolverData,
  MachineresolverService,
  MachineresolverServiceInterface
} from "../../../services/machineresolver/machineresolver.service";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import {
  DialogServiceInterface,
  DialogService,
  MatDialogConfigRequired
} from "../../../services/dialog/dialog.service";
import { ConfirmationDialogData } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { MachineresolverHostsTabComponent } from "../machineresolver-hosts-tab/machineresolver-hosts-tab.component";
import { MachineresolverLdapTabComponent } from "../machineresolver-ldap-tab/machineresolver-ldap-tab.component";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";

@Component({
  selector: "app-machineresolver-panel-edit",
  templateUrl: "./machineresolver-panel-edit.component.html",
  styleUrls: ["./machineresolver-panel-edit.component.scss"],
  imports: [
    CommonModule,
    MatExpansionModule,
    MatIconModule,
    MatInputModule,
    MatAutocompleteModule,
    MatSelectModule,
    FormsModule,
    MatButtonModule,
    MatIcon,
    MachineresolverHostsTabComponent,
    MachineresolverLdapTabComponent
  ]
})
export class MachineresolverPanelEditComponent {
  readonly machineresolverService: MachineresolverServiceInterface = inject(MachineresolverService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly machineresolverTypes = this.machineresolverService.allMachineresolverTypes;
  readonly machineresolvers = this.machineresolverService.machineresolvers();
  readonly isEdited = computed(
    () => JSON.stringify(this.currentMachineresolver()) !== JSON.stringify(this.originalMachineresolver())
  );
  readonly dataValidatorSignal = signal<(data: MachineresolverData) => boolean>(() => true);
  readonly isEditMode = signal<boolean>(false);

  readonly originalMachineresolver = input.required<Machineresolver>();
  readonly editedMachineresolver: WritableSignal<Machineresolver> = linkedSignal({
    source: () => ({ originalMachineresolver: this.originalMachineresolver(), isEditMode: this.isEditMode() }),
    computation: (source) => {
      return deepCopy(source.originalMachineresolver);
    }
  });
  readonly currentMachineresolver = linkedSignal<Machineresolver>(() =>
    this.isEditMode() ? this.editedMachineresolver() : this.originalMachineresolver()
  );

  onNewData(newData: MachineresolverData) {
    this.editedMachineresolver.set({ ...this.currentMachineresolver(), data: newData });
  }
  onNewValidator(newValidator: (data: MachineresolverData) => boolean) {
    this.dataValidatorSignal.set(newValidator);
  }
  readonly canSaveMachineresolver = computed(() => {
    const current = this.currentMachineresolver();
    if (!current.resolvername.trim()) return false;
    const dataValidator = this.dataValidatorSignal();
    return dataValidator(current.data);
  });

  onMachineresolverTypeChange(newType: string) {
    const current = this.currentMachineresolver();
    this.editedMachineresolver.set({
      ...current,
      type: newType,
      data: { resolver: current.resolvername, type: newType } // Reset data to only have resolver field
    });
  }

  onResolvernameChange(newName: string) {
    const current = this.currentMachineresolver();
    this.editedMachineresolver.set({
      ...current,
      resolvername: newName,
      data: { ...current.data, resolver: newName } // Keep data.resolver in sync with name
    });
  }

  onUpdateResolverData(newData: MachineresolverData) {
    const current = this.currentMachineresolver();
    if (newData.type !== current.type) {
      console.error("Type mismatch between new data and current machineresolver type");
      return;
    }
    this.editedMachineresolver.set({
      ...current,
      data: newData
    });
  }

  async saveMachineresolver() {
    const current = this.currentMachineresolver();
    try {
      await this.machineresolverService.postTestMachineresolver(current);
    } catch (error) {
      const errorMessage = (error as Error).message;
      if (errorMessage === "post-failed") {
        const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
          data: {
            type: "machineresolver",
            title: "Save machineresolver despite test failure?",
            action: "proceed-despite-error"
          }
        };
        const result = await this.dialogService.confirm(dialogData);
        if (!result) return;
      } else {
        return;
      }
    }
    try {
      await this.machineresolverService.postMachineresolver(current);
    } catch (error) {
      return;
    }
    this.isEditMode.set(false);
  }

  async deleteMachineresolver() {
    const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
      data: {
        type: "machineresolver",
        title: "Delete machineresolver",
        action: "delete",
        serialList: [this.currentMachineresolver().resolvername]
      }
    };
    this.dialogService
      .confirm(dialogData)
      .then(async (result) => {
        if (!result) {
          return;
        }
        try {
          await this.machineresolverService.deleteMachineresolver(this.currentMachineresolver().resolvername);
        } catch (error) {
          return;
        }
      })
      .catch((err) => {
        console.error("Error handling delete machineresolver dialog:", err);
      });
    return;
  }

  cancelEditMode() {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
      return;
    }
    const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
      data: {
        type: "machineresolver",
        title: "Discard changes",
        action: "discard"
      }
    };
    this.dialogService
      .confirm(dialogData)
      .then((result) => {
        if (result) {
          this.isEditMode.set(false);
        }
      })
      .catch((err) => {
        console.error("Error handling unsaved changes dialog:", err);
      });
    return;
  }

  handleCollapse($panel: MatExpansionPanel) {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
      return;
    }
    const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
      data: {
        type: "machineresolver",
        title: "Discard changes",
        action: "discard"
      }
    };
    this.dialogService
      .confirm(dialogData)
      .then((result) => {
        if (result) {
          this.isEditMode.set(false);
          $panel.close();
        } else {
          $panel.open();
        }
      })
      .catch((err) => {
        console.error("Error handling unsaved changes dialog:", err);
      });
    return;
  }
}

// Remove this when the global helper functions is merged
function deepCopy<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}
