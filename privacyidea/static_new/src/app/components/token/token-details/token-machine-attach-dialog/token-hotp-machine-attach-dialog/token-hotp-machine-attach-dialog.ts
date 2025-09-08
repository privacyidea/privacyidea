import { Component, computed, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators
} from "@angular/forms";
import { MatOptionModule } from "@angular/material/core";
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from "@angular/material/dialog";
import {
  ApplicationService,
  ApplicationServiceInterface
} from "../../../../../services/application/application.service";
import { Machine, MachineService, MachineServiceInterface } from "../../../../../services/machine/machine.service";
import { UserService, UserServiceInterface } from "../../../../../services/user/user.service";

import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatDividerModule } from "@angular/material/divider";
import { MatSelectModule } from "@angular/material/select";

import { MatButtonModule } from "@angular/material/button";
import { MatInputModule } from "@angular/material/input";
import { Observable } from "rxjs";

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
    MatAutocompleteModule
  ]
})
export class TokenHotpMachineAssignDialogComponent {
  public dialogRef: MatDialogRef<TokenHotpMachineAssignDialogComponent, Observable<any> | null> = inject(MatDialogRef);
  private machineService: MachineServiceInterface = inject(MachineService);

  public data: HotpMachineAssignDialogData = inject(MAT_DIALOG_DATA);
  public tokenSerial = this.data.tokenSerial;

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

  onCancel(): void {
    this.dialogRef.close(null);
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
