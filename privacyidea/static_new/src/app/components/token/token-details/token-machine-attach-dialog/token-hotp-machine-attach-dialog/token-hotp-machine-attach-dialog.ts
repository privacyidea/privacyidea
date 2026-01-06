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
import { Component, inject } from "@angular/core";
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators
} from "@angular/forms";
import { MatOptionModule } from "@angular/material/core";
import { MatDialogModule } from "@angular/material/dialog";
import { Machine, MachineService, MachineServiceInterface } from "../../../../../services/machine/machine.service";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatDividerModule } from "@angular/material/divider";
import { MatSelectModule } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatInputModule } from "@angular/material/input";
import { Observable } from "rxjs";
import { AbstractDialogComponent } from "../../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "../../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "../../../../../models/dialog";

export type HotpMachineAssignDialogData = {
  tokenSerial: string;
};

@Component({
  selector: "token-ssh-machine-attach-dialog",
  styleUrls: ["./token-hotp-machine-attach-dialog.component.scss"],
  templateUrl: "./token-hotp-machine-attach-dialog.component.html",
  standalone: true,
  imports: [
    ReactiveFormsModule,
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
export class TokenHotpMachineAssignDialogComponent extends AbstractDialogComponent<
  HotpMachineAssignDialogData,
  Observable<any> | null
> {
  private machineService: MachineServiceInterface = inject(MachineService);
  public tokenSerial = this.data.tokenSerial;

  assignAction: DialogAction<string> = {
    label: "Assign",
    value: "assign",
    type: "confirm"
  };
  onAction(actionValue: string): void {
    if (actionValue === "assign") {
      this.onAssign();
    }
  }

  countControl = new FormControl<number | null>(100, {
    nonNullable: true,
    validators: [Validators.required, Validators.min(10)]
  });

  roundsControl = new FormControl<number | null>(10000, {
    nonNullable: true,
    validators: [Validators.required, Validators.min(1000)]
  });

  formGroup = new FormGroup({
    count: this.countControl,
    rounds: this.roundsControl
  });

  onAssign() {
    if (this.formGroup.invalid) return;

    const request = this.machineService.postAssignMachineToToken({
      application: "offline",
      count: this.countControl.value!,
      machineid: 0,
      resolver: "",
      rounds: this.roundsControl.value!,
      serial: this.data.tokenSerial
    });
    request.subscribe({
      next: (_) => {
        // Subscribed to ensure that the request will be executed
      },
      error: (error) => {
        console.error("Error during assignment request:", error);
      }
    });
    this.dialogRef.close(request);
  }

  machineValidator(control: AbstractControl<string | Machine>): ValidationErrors | null {
    if (!control.value) {
      return { required: true }; // Machine selection is required
    }
    if (typeof control.value === "string") {
      return { required: true }; // Machine selection is required
    }
    const machine = control.value as Machine;
    if (!machine.id || !machine.hostname || !machine.ip || !machine.resolver_name) {
      return { invalidMachine: true }; // Invalid machine object
    }
    return null; // No validation error
  }
}
