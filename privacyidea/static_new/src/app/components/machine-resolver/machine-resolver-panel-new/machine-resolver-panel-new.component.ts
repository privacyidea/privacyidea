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

import { Component, computed, inject, OnDestroy, OnInit, signal } from "@angular/core";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatExpansionModule, MatExpansionPanel } from "@angular/material/expansion";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MachineResolverHostsTabComponent } from "@components/machine-resolver/machine-resolver-hosts-tab/machine-resolver-hosts-tab.component";
import { MachineResolverLdapTabComponent } from "@components/machine-resolver/machine-resolver-ldap-tab/machine-resolver-ldap-tab.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import {
  MachineResolver,
  MachineResolverData,
  MachineResolverService,
  MachineResolverServiceInterface
} from "@services/machine-resolver/machine-resolver.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { lastValueFrom } from "rxjs";

@Component({
  selector: "app-machine-resolver-panel-new",
  templateUrl: "./machine-resolver-panel-new.component.html",
  styleUrls: ["./machine-resolver-panel-new.component.scss"],
  imports: [
    MatExpansionModule,
    MatIconModule,
    MatInputModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatButtonModule,
    MatIcon,
    MachineResolverHostsTabComponent,
    MachineResolverLdapTabComponent
  ]
})
export class MachineResolverPanelNewComponent implements OnInit, OnDestroy {
  readonly machineResolverService: MachineResolverServiceInterface = inject(MachineResolverService);
  readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly pendingChangesService = inject(PendingChangesService);

  ngOnInit(): void {
    this.pendingChangesService.registerHasChanges(() => this.isEdited());
    this.pendingChangesService.registerValidChanges(() => this.canSaveMachineResolver());
    this.pendingChangesService.registerSave(() => this.saveMachineResolver());
  }

  ngOnDestroy(): void {
    this.pendingChangesService.clearAllRegistrations();
  }

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
  readonly nameHasPatternError = computed(() => {
    const name = this.newMachineResolver().resolvername;
    return name.length > 0 && !/^[a-zA-Z0-9._-]*$/.test(name);
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
    if (!current.resolvername.trim() || !/^[a-zA-Z0-9._-]*$/.test(current.resolvername)) return false;

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

  async saveMachineResolver(panel?: MatExpansionPanel): Promise<boolean> {
    const current = this.newMachineResolver();
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
                title: $localize`Save machine resolver despite test failure?`,
                confirmAction: { label: $localize`Proceed`, value: true, type: "destruct" },
                items: [current.resolvername || $localize`New Machine Resolver`],
                itemType: "machine resolver"
              }
            })
            .afterClosed()
        );
        if (!result) return false;
      } else {
        return false;
      }
    }
    try {
      await this.machineResolverService.postMachineResolver(current);
    } catch {
      return false;
    }
    this.resetMachineResolver();
    panel?.close();
    return true;
  }

  handleCollapse($panel: MatExpansionPanel) {
    if (!this.isEdited()) {
      this.newMachineResolver.set(this.machineResolverDefault);
      return;
    }
    this.dialogService
      .openDialog({
        component: SaveAndExitDialogComponent,
        data: {
          title: $localize`Discard changes`,
          allowSaveExit: this.canSaveMachineResolver(),
          saveExitDisabled: !this.canSaveMachineResolver()
        }
      })
      .afterClosed()
      .subscribe({
        next: async (result) => {
          if (result === "save-exit") {
            if (!this.canSaveMachineResolver()) {
              $panel.open();
              return;
            }
            await this.saveMachineResolver($panel);
          } else if (result === "discard") {
            this.resetMachineResolver();
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
