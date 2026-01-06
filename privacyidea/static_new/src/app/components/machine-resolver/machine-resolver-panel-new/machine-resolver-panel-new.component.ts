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

import { Component, computed, inject, signal } from "@angular/core";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatSelectModule } from "@angular/material/select";
import {
  MachineResolver,
  MachineResolverData,
  MachineResolverService,
  MachineResolverServiceInterface
} from "../../../services/machine-resolver/machine-resolver.service";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatButtonModule } from "@angular/material/button";
import {
  DialogService,
  DialogServiceInterface,
  MatDialogConfigRequired
} from "../../../services/dialog/dialog.service";
import { ConfirmationDialogData } from "../../shared/confirmation-dialog/confirmation-dialog.component";
import { MachineResolverHostsTabComponent } from "../machine-resolver-hosts-tab/machine-resolver-hosts-tab.component";
import { MachineResolverLdapTabComponent } from "../machine-resolver-ldap-tab/machine-resolver-ldap-tab.component";

@Component({
  selector: "app-machine-resolver-panel-new",
  templateUrl: "./machine-resolver-panel-new.component.html",
  styleUrls: ["./machine-resolver-panel-new.component.scss"],
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
export class MachineResolverPanelNewComponent {
  readonly machineResolverService: MachineResolverServiceInterface = inject(MachineResolverService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);

  readonly machineResolverDefault: MachineResolver = {
    resolvername: "",
    type: "hosts",
    data: { resolver: "", type: "hosts" }
  };
  readonly newMachineResolver = signal<MachineResolver>(this.machineResolverDefault);
  resetMachineResolver() {
    this.newMachineResolver.set(this.machineResolverDefault);
  }
  readonly machineResolverTypes = this.machineResolverService.allMachineResolverTypes;
  readonly machineResolvers = this.machineResolverService.machineResolvers();
  readonly isEdited = computed(() => {
    const current = this.newMachineResolver();
    if (current.resolvername.trim() !== "") return true;
    if (Object.keys(current.data).length > 2) return true; // More than resolver and type fields
    return false;
  });
  readonly dataValidatorSignal = signal<(data: MachineResolverData) => boolean>(() => true);

  onNewData(newData: MachineResolverData) {
    this.newMachineResolver.set({ ...this.newMachineResolver(), data: newData });
  }
  onNewValidator(newValidator: (data: MachineResolverData) => boolean) {
    this.dataValidatorSignal.set(newValidator);
  }

  readonly canSaveMachineResolver = computed(() => {
    const current = this.newMachineResolver();
    if (!current.resolvername.trim()) return false;

    const dataValidator = this.dataValidatorSignal();
    return dataValidator(current.data);
  });

  onMachineResolverTypeChange(newType: string) {
    const current = this.newMachineResolver();
    this.newMachineResolver.set({
      ...current,
      type: newType,
      data: { resolver: current.resolvername, type: newType } // Reset data to only have resolver field
    });
  }
  onResolvernameChange(newName: string) {
    const current = this.newMachineResolver();
    this.newMachineResolver.set({
      ...current,
      resolvername: newName,
      data: { ...current.data, resolver: newName } // Keep data.resolver in sync with name
    });
  }

  onUpdateResolverData(newData: MachineResolverData) {
    if (newData.type !== this.newMachineResolver().type) {
      console.error("Type mismatch between new data and current machineResolver type");
      return;
    }
    const current = this.newMachineResolver();
    this.newMachineResolver.set({
      ...current,
      data: newData
    });
  }

  async saveMachineResolver(panel: MatExpansionPanel) {
    const current = this.newMachineResolver();
    try {
      await this.machineResolverService.postTestMachineResolver(current);
    } catch (error) {
      const errorMessage = (error as Error).message;
      if (errorMessage === "post-failed") {
        const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
          data: {
            type: "machineResolver",
            title: "Save machineResolver despite test failure?",
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
      await this.machineResolverService.postMachineResolver(current);
    } catch (error) {
      return;
    }
    this.resetMachineResolver();
    panel.close();
  }

  handleCollapse($panel: MatExpansionPanel) {
    if (!this.isEdited()) {
      this.newMachineResolver.set(this.machineResolverDefault);
      return;
    }
    const dialogData: MatDialogConfigRequired<ConfirmationDialogData> = {
      data: {
        type: "machineResolver",
        title: "Discard changes",
        action: "discard"
      }
    };
    this.dialogService
      .confirm(dialogData)
      .then((result) => {
        if (result) {
          this.resetMachineResolver();
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
