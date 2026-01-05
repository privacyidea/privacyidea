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
  MachineResolver,
  MachineResolverData,
  MachineResolverService,
  MachineResolverServiceInterface
} from "../../../services/machine-resolver/machine-resolver.service";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { DialogServiceInterface, DialogService } from "../../../services/dialog/dialog.service";
import { MachineResolverLdapTabComponent } from "../machine-resolver-ldap-tab/machine-resolver-ldap-tab.component";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { MachineResolverHostsTabComponent } from "../machine-resolver-hosts-tab/machine-resolver-hosts-tab.component";
import { deepCopy } from "../../../utils/deep-copy.utils";
import { SimpleConfirmationDialogComponent } from "../../shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { lastValueFrom } from "rxjs";

@Component({
  selector: "app-machine-resolver-panel-edit",
  templateUrl: "./machine-resolver-panel-edit.component.html",
  styleUrls: ["./machine-resolver-panel-edit.component.scss"],
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
    MachineResolverHostsTabComponent,
    MachineResolverLdapTabComponent
  ]
})
export class MachineResolverPanelEditComponent {
  readonly machineResolverService: MachineResolverServiceInterface = inject(MachineResolverService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly authService: AuthServiceInterface = inject(AuthService);

  readonly machineResolverTypes = this.machineResolverService.allMachineResolverTypes;
  readonly machineResolvers = this.machineResolverService.machineResolvers();
  readonly isEdited = computed(
    () => JSON.stringify(this.currentMachineResolver()) !== JSON.stringify(this.originalMachineResolver())
  );
  readonly dataValidatorSignal = signal<(data: MachineResolverData) => boolean>(() => true);
  readonly isEditMode = signal<boolean>(false);

  readonly originalMachineResolver = input.required<MachineResolver>();
  readonly editedMachineResolver: WritableSignal<MachineResolver> = linkedSignal({
    source: () => ({ originalMachineResolver: this.originalMachineResolver(), isEditMode: this.isEditMode() }),
    computation: (source) => deepCopy(source.originalMachineResolver)
  });
  readonly currentMachineResolver = linkedSignal<MachineResolver>(() =>
    this.isEditMode() ? this.editedMachineResolver() : this.originalMachineResolver()
  );

  onNewData(newData: MachineResolverData) {
    this.editedMachineResolver.set({ ...this.currentMachineResolver(), data: newData });
  }
  onNewValidator(newValidator: (data: MachineResolverData) => boolean) {
    this.dataValidatorSignal.set(newValidator);
  }
  readonly canSaveMachineResolver = computed(() => {
    const current = this.currentMachineResolver();
    if (!current.resolvername.trim()) return false;
    const dataValidator = this.dataValidatorSignal();
    return dataValidator(current.data);
  });

  onMachineResolverTypeChange(newType: string) {
    const current = this.currentMachineResolver();
    this.editedMachineResolver.set({
      ...current,
      type: newType,
      data: { resolver: current.resolvername, type: newType } // Reset data to only have resolver field
    });
  }

  onResolvernameChange(newName: string) {
    const current = this.currentMachineResolver();
    this.editedMachineResolver.set({
      ...current,
      resolvername: newName,
      data: { ...current.data, resolver: newName } // Keep data.resolver in sync with name
    });
  }

  onUpdateResolverData(newData: MachineResolverData) {
    const current = this.currentMachineResolver();
    if (newData.type !== current.type) {
      console.error("Type mismatch between new data and current machineResolver type");
      return;
    }
    this.editedMachineResolver.set({
      ...current,
      data: newData
    });
  }

  async saveMachineResolver() {
    const current = this.currentMachineResolver();
    try {
      await this.machineResolverService.postTestMachineResolver(current);
    } catch (error) {
      const errorMessage = (error as Error).message;
      if (errorMessage === "post-failed") {
        const result = await lastValueFrom(
          this.dialogService
            .openDialog({
              component: SimpleConfirmationDialogComponent,
              data: {
                title: "Save machineResolver despite test failure?",
                items: [],
                itemType: "machineResolver",
                confirmAction: { label: "Save", value: true, type: "confirm" },
                cancelAction: { label: "Cancel", value: false, type: "cancel" }
              }
            })
            .afterClosed()
        );
        if (!result) return;
      } else {
        return;
      }
    }
    try {
      await this.machineResolverService.postMachineResolver(current);
    } catch (error) {
      return;
    }
    this.isEditMode.set(false);
  }

  async deleteMachineResolver() {
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Delete machine resolver",
          items: [this.currentMachineResolver().resolvername || "Unnamed Machine Resolver"],
          itemType: "machine resolver",
          confirmAction: { label: "Delete", value: true, type: "destruct" }
        }
      })
      .afterClosed()
      .subscribe({
        next: async (result) => {
          if (result) {
            try {
              await this.machineResolverService.deleteMachineResolver(this.currentMachineResolver().resolvername);
            } catch (error) {
              return;
            }
          }
        },
        error: (err) => {
          console.error("Error handling delete machine resolver dialog:", err);
        }
      });
    return;
  }

  cancelEditMode() {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
      return;
    }

    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Discard changes",
          items: [this.currentMachineResolver().resolvername || "Unnamed Machine Resolver"],
          itemType: "machine resolver",
          confirmAction: { label: "Discard", value: true, type: "destruct" },
          cancelAction: { label: "Cancel", value: false, type: "cancel" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.isEditMode.set(false);
          }
        },
        error: (err) => {
          console.error("Error handling unsaved changes dialog:", err);
        }
      });
    return;
  }

  handleCollapse($panel: MatExpansionPanel) {
    if (!this.isEdited()) {
      this.isEditMode.set(false);
      return;
    }
    this.dialogService
      .openDialog({
        component: SimpleConfirmationDialogComponent,
        data: {
          title: "Discard changes",
          items: [this.currentMachineResolver().resolvername || "Unnamed Machine Resolver"],
          itemType: "machine resolver",
          confirmAction: { label: "Discard", value: true, type: "destruct" },
          cancelAction: { label: "Cancel", value: false, type: "cancel" }
        }
      })
      .afterClosed()
      .subscribe({
        next: (result) => {
          if (result) {
            this.isEditMode.set(false);
            $panel.close();
          } else {
            $panel.open();
          }
        },
        error: (err) => {
          console.error("Error handling unsaved changes dialog:", err);
        }
      });
    return;
  }
}
