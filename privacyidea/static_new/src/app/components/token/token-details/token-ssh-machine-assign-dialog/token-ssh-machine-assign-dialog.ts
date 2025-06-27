import {
  Component,
  computed,
  Inject,
  linkedSignal,
  signal,
  WritableSignal,
} from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import {
  Machine,
  MachineService,
} from '../../../../services/machine/machine.service';
import { ApplicationService } from '../../../../services/application/application.service';
import { UserService } from '../../../../services/user/user.service';
import { MatOptionModule } from '@angular/material/core';

import { MatSelectModule } from '@angular/material/select';
import { MatDividerModule } from '@angular/material/divider';
import { MatAutocompleteModule } from '@angular/material/autocomplete';

import { Observable } from 'rxjs';
import {
  EnrollmentResponse,
  TokenEnrollmentData,
} from '../../../../mappers/token-api-payload/_token-api-payload.mapper';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'token-ssh-machine-assign-dialog',
  styleUrls: ['./token-ssh-machine-assign-dialog.component.scss'],
  templateUrl: './token-ssh-machine-assign-dialog.component.html',
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
  ],
})
export class TokenSshMachineAssignDialogComponent {
  /// Data for the dialog ///
  availableApplications = linkedSignal({
    source: this.applicationService.applications,
    computation: (source) => {
      var availableApps = [];
      if (source.ssh.options.sshkey.service_id.value.length > 0) {
        availableApps.push('ssh');
      }
      // TODO: Add other applications
      return availableApps;
    },
  });
  availableMachines = this.machineService.machines;
  availableServiceIds: WritableSignal<string[]> = linkedSignal({
    source: this.applicationService.applications,
    computation: (source) => {
      const sshApp = source.ssh;
      return sshApp?.options.sshkey.service_id.value || [];
    },
  });
  availableUsers: WritableSignal<string[]> = linkedSignal({
    source: this.userService.users,
    computation: () => this.userService.users().map((user) => user.username),
  });

  machineFilter: WritableSignal<string> = signal('');
  filteredMachines = computed(() => {
    const filterString = this.machineFilter().trim().toLowerCase();
    if (!filterString) {
      return this.availableMachines();
    }
    return this.availableMachines().filter((machine) =>
      this.getFullMachineName(machine).toLowerCase().includes(filterString),
    );
  });

  userFilter: WritableSignal<string> = signal('');
  filteredUsers = computed(() => {
    const filterString = this.userFilter().trim().toLowerCase();
    if (!filterString) {
      return this.availableUsers();
    }
    return this.availableUsers().filter((user) =>
      user.toLowerCase().includes(filterString),
    );
  });

  /// Form controls ///
  selectedApplication = new FormControl<string>('ssh', Validators.required);
  selectedMachine = new FormControl<string | Machine>(
    '',
    this.machineValidator,
  );
  selectedServiceId = new FormControl<string>('', Validators.required);
  selectedUser = new FormControl<string>('', Validators.required);

  formGroup = new FormGroup({
    selectedApplication: this.selectedApplication,
    selectedMachine: this.selectedMachine,
    selectedServiceId: this.selectedServiceId,
    selectedUser: this.selectedUser,
  });

  /// Computed properties ///
  constructor(
    private applicationService: ApplicationService,
    private machineService: MachineService,
    private userService: UserService,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      tokenSerial: string;
      tokenDetails: Record<string, any>;
      tokenType: string;
    },
    public dialogRef: MatDialogRef<
      TokenSshMachineAssignDialogComponent,
      Observable<any> | null
    >,
  ) {}

  ngOnInit() {
    this.selectedMachine.valueChanges.subscribe((value) => {
      this.machineFilter.set(
        typeof value === 'string'
          ? value.trim().toLowerCase()
          : value
            ? this.getFullMachineName(value).trim().toLowerCase()
            : '',
      );
      this.selectedUser.valueChanges.subscribe((userValue) => {
        this.userFilter.set(userValue ? userValue.trim().toLowerCase() : '');
      });
    });
  }

  /// Methods ///
  getFullMachineName(machine: string | Machine): string {
    if (typeof machine === 'string') {
      return machine;
    }
    return `${machine.hostname.join(', ')} [${machine.id}] (${machine.ip} in ${machine.resolver_name})`;
  }

  onAssign() {
    if (this.formGroup.invalid) {
      return;
    }
    const machine = this.selectedMachine.value;
    if (!machine || typeof machine === 'string') {
      console.error('Invalid machine selection:', machine);
      return;
    }
    const args = {
      service_id: this.selectedServiceId.value!,
      user: this.selectedUser.value!,
      serial: this.data.tokenSerial,
      application: this.selectedApplication.value!,
      machineid: machine!.id,
      resolver: machine!.resolver_name,
    };
    const request = this.machineService.postAssignMachineToToken(args);
    request.subscribe({
      next: (response) => {},
      error: (error) => {
        console.error('Error during assignment request:', error);
      },
    });
    this.dialogRef.close(request);
  }
  onCancel(): void {
    this.dialogRef.close(null);
  }

  machineValidator(
    control: AbstractControl<string | Machine>,
  ): ValidationErrors | null {
    if (!control.value) {
      return { required: true }; // Machine selection is required
    }
    if (typeof control.value === 'string') {
      return { required: true }; // Machine selection is required
    }
    const machine = control.value as Machine;
    if (
      !machine.id ||
      !machine.hostname ||
      !machine.ip ||
      !machine.resolver_name
    ) {
      return { invalidMachine: true }; // Invalid machine object
    }
    return null; // No validation error
  }
}
