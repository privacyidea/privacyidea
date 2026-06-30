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
import { Component, computed, effect, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { form, FormField, required, validate } from "@angular/forms/signals";
import { MatOptionModule } from "@angular/material/core";
import { MatDialogModule } from "@angular/material/dialog";
import { ApplicationService, ApplicationServiceInterface } from "@services/application/application.service";
import { Machine, MachineService, MachineServiceInterface } from "@services/machine/machine.service";
import { TokenDetails } from "@services/token/token.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";

import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatDividerModule } from "@angular/material/divider";
import { MatSelectModule } from "@angular/material/select";

import { MatButtonModule } from "@angular/material/button";
import { MatInputModule } from "@angular/material/input";
import { PiResponse } from "@app/app.component";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { Observable } from "rxjs";

export interface SshMachineAssignDialogData {
  tokenSerial: string;
  tokenDetails: TokenDetails;
  tokenType: string;
}

@Component({
  selector: "app-token-ssh-machine-attach-dialog",
  styleUrls: ["./token-ssh-machine-attach-dialog.component.scss"],
  templateUrl: "./token-ssh-machine-attach-dialog.component.html",
  standalone: true,
  imports: [
    FormField,
    MatSelectModule,
    MatInputModule,
    MatButtonModule,
    MatDialogModule,
    MatOptionModule,
    MatSelectModule,
    MatDividerModule,
    MatAutocompleteModule,
    DialogWrapperComponent
  ]
})
export class TokenSshMachineAssignDialogComponent extends AbstractDialogComponent<
  SshMachineAssignDialogData,
  Observable<PiResponse<number>> | null
> {
  /// Data for the dialog ///
  private applicationService: ApplicationServiceInterface = inject(ApplicationService);
  private machineService: MachineServiceInterface = inject(MachineService);
  private userService: UserServiceInterface = inject(UserService);

  assignAction: DialogAction<string> = {
    label: $localize`Assign`,
    value: "assign",
    type: "confirm",
    primary: true
  };
  onAction(actionValue: string): void {
    if (actionValue === "assign") {
      this.onAssign();
    } else {
      this.onCancel();
    }
  }

  availableApplications = linkedSignal({
    source: this.applicationService.applications,
    computation: (source) => {
      const availableApps = [];
      if (source.ssh.options.sshkey.service_id.value.length > 0) {
        availableApps.push("ssh");
      }
      // TODO: Add other applications
      return availableApps;
    }
  });

  availableServiceIds: WritableSignal<string[]> = linkedSignal({
    source: this.applicationService.applications,
    computation: (source) => {
      const sshApp = source.ssh;
      return sshApp?.options.sshkey.service_id.value || [];
    }
  });
  availableUsers: WritableSignal<string[]> = linkedSignal({
    source: this.userService.users,
    computation: () => this.userService.users().map((user) => user.username)
  });

  machineFilter = signal("");
  filteredMachines = computed(() => {
    const filterString = this.machineFilter().trim().toLowerCase();
    if (!filterString) return this.machineService.machines();
    return this.machineService
      .machines()
      ?.filter((machine) => this.getFullMachineName(machine).toLowerCase().includes(filterString));
  });

  userFilter = signal("");
  filteredUsers = computed(() => {
    const filterString = this.userFilter().trim().toLowerCase();
    if (!filterString) {
      return this.availableUsers();
    }
    return this.availableUsers().filter((user) => user.toLowerCase().includes(filterString));
  });

  /// Signal form fields ///
  selectedMachineValue = signal<string | Machine>("");
  selectedMachineForm = form(this.selectedMachineValue, (f) => {
    validate(f, (ctx) => {
      const value = ctx.value();
      if (!value) return [{ kind: "required" }];
      if (typeof value === "string") return [{ kind: "required" }];
      const machine = value as Machine;
      if (!machine.id || !machine.hostname || !machine.ip || !machine.resolver_name) {
        return [{ kind: "invalidMachine" }];
      }
      return [];
    });
  });

  selectedServiceIdValue = signal("");
  selectedServiceIdForm = form(this.selectedServiceIdValue, (f) => {
    required(f);
  });

  selectedUserValue = signal("");
  selectedUserForm = form(this.selectedUserValue, (f) => {
    required(f);
  });

  isFormValid = computed(
    () => this.selectedMachineForm().valid() && this.selectedServiceIdForm().valid() && this.selectedUserForm().valid()
  );

  constructor() {
    super();
    effect(() => {
      const value = this.selectedMachineValue();
      this.machineFilter.set(
        typeof value === "string"
          ? value.trim().toLowerCase()
          : value
            ? this.getFullMachineName(value).trim().toLowerCase()
            : ""
      );
    });
    effect(() => {
      const userValue = this.selectedUserValue();
      this.userFilter.set(userValue ? userValue.trim().toLowerCase() : "");
    });
  }

  /// Methods ///
  getFullMachineName(machine: string | Machine): string {
    if (typeof machine === "string") {
      return machine;
    }
    return `${machine.hostname.join(", ")} [${machine.id}] (${machine.ip} in ${machine.resolver_name})`;
  }

  onAssign() {
    if (!this.isFormValid()) {
      this.selectedMachineForm().markAsTouched();
      this.selectedServiceIdForm().markAsTouched();
      this.selectedUserForm().markAsTouched();
      return;
    }
    const machine = this.selectedMachineValue();
    if (!machine || typeof machine === "string") {
      console.error("Invalid machine selection:", machine);
      return;
    }
    const request = this.machineService.postAssignMachineToToken({
      service_id: this.selectedServiceIdValue(),
      user: this.selectedUserValue(),
      serial: this.data.tokenSerial,
      application: "ssh",
      machineid: machine!.id,
      resolver: machine!.resolver_name
    });
    request.subscribe({
      next: () => {
        this.machineService.machinesResource.reload();
        this.machineService.tokenApplicationResource.reload();
      },
      error: (error) => {
        console.error("Error during assignment request:", error);
      }
    });
    this.dialogRef.close(request);
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }
}
