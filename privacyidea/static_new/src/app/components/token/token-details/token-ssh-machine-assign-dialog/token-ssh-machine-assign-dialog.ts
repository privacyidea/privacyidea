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
import { ApplicationService, ApplicationServiceInterface } from "../../../../services/application/application.service";
import { Machine, MachineService, MachineServiceInterface } from "../../../../services/machine/machine.service";
import { UserService, UserServiceInterface } from "../../../../services/user/user.service";

import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { MatDividerModule } from "@angular/material/divider";
import { MatSelectModule } from "@angular/material/select";

import { MatButtonModule } from "@angular/material/button";
import { MatInputModule } from "@angular/material/input";
import { Observable } from "rxjs";

@Component({
  selector: "token-ssh-machine-assign-dialog",
  styleUrls: ["./token-ssh-machine-assign-dialog.component.scss"],
  templateUrl: "./token-ssh-machine-assign-dialog.component.html",
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
export class TokenSshMachineAssignDialogComponent {
  /// Data for the dialog ///
  private applicationService: ApplicationServiceInterface = inject(ApplicationService);
  private machineService: MachineServiceInterface = inject(MachineService);
  private userService: UserServiceInterface = inject(UserService);
  public data: {
    tokenSerial: string;
    tokenDetails: Record<string, any>;
    tokenType: string;
  } = inject(MAT_DIALOG_DATA);
  public dialogRef: MatDialogRef<TokenSshMachineAssignDialogComponent, Observable<any> | null> = inject(MatDialogRef);

  availableApplications = linkedSignal({
    source: this.applicationService.applications,
    computation: (source) => {
      var availableApps = [];
      if (source.ssh.options.sshkey.service_id.value.length > 0) {
        availableApps.push("ssh");
      }
      // TODO: Add other applications
      return availableApps;
    }
  });
  availableMachines = this.machineService.machines;
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

  machineFilter: WritableSignal<string> = signal("");
  filteredMachines = computed(() => {
    const filterString = this.machineFilter().trim().toLowerCase();
    if (!filterString) {
      return this.availableMachines();
    }
    return this.availableMachines()?.filter((machine) =>
      this.getFullMachineName(machine).toLowerCase().includes(filterString)
    );
  });

  userFilter: WritableSignal<string> = signal("");
  filteredUsers = computed(() => {
    const filterString = this.userFilter().trim().toLowerCase();
    if (!filterString) {
      return this.availableUsers();
    }
    return this.availableUsers().filter((user) => user.toLowerCase().includes(filterString));
  });

  /// Form controls ///
  selectedApplication = new FormControl<string>("ssh", Validators.required);
  selectedMachine = new FormControl<string | Machine>("", this.machineValidator);
  selectedServiceId = new FormControl<string>("", Validators.required);
  selectedUser = new FormControl<string>("", Validators.required);

  formGroup = new FormGroup({
    selectedApplication: this.selectedApplication,
    selectedMachine: this.selectedMachine,
    selectedServiceId: this.selectedServiceId,
    selectedUser: this.selectedUser
  });

  /// Computed properties ///

  ngOnInit() {
    this.selectedMachine.valueChanges.subscribe((value) => {
      this.machineFilter.set(
        typeof value === "string"
          ? value.trim().toLowerCase()
          : value
            ? this.getFullMachineName(value).trim().toLowerCase()
            : ""
      );
      this.selectedUser.valueChanges.subscribe((userValue) => {
        this.userFilter.set(userValue ? userValue.trim().toLowerCase() : "");
      });
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
    if (this.formGroup.invalid) {
      return;
    }
    const machine = this.selectedMachine.value;
    if (!machine || typeof machine === "string") {
      console.error("Invalid machine selection:", machine);
      return;
    }
    const args = {
      service_id: this.selectedServiceId.value!,
      user: this.selectedUser.value!,
      serial: this.data.tokenSerial,
      application: this.selectedApplication.value!,
      machineid: machine!.id,
      resolver: machine!.resolver_name
    };
    const request = this.machineService.postAssignMachineToToken(args);
    request.subscribe({
      next: (response) => {},
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
