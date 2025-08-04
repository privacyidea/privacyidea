import {
  Component,
  computed,
  inject,
  signal,
  WritableSignal,
} from '@angular/core';
import {
  MatDialogActions,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import {
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
  MatOption,
} from '@angular/material/autocomplete';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatSelect } from '@angular/material/select';
import { UserData, UserService } from '../../../../services/user/user.service';
import { TokenService } from '../../../../services/token/token.service';
import { RealmService } from '../../../../services/realm/realm.service';
import { MatInput } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';

export interface SelectedUserAssignResult {
  username: string;
  realm: string;
  pin?: string | null;
}

@Component({
  selector: 'app-selected-user-assign-dialog',
  imports: [
    FormsModule,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatError,
    MatFormField,
    MatLabel,
    MatSelect,
    ReactiveFormsModule,
    MatOption,
    MatInput,
    MatIcon,
    MatDialogActions,
    MatButtonModule,
    MatDialogTitle,
    MatDialogContent,
  ],
  templateUrl: './selected-user-assign-dialog.component.html',
  styleUrl: './selected-user-assign-dialog.component.scss',
})
export class SelectedUserAssignDialogComponent {
  pin: WritableSignal<string> = signal('');
  pinRepeat: WritableSignal<string> = signal('');
  hidePin: WritableSignal<boolean> = signal(true);
  pinsMatch = computed(() => this.pin() === this.pinRepeat());
  protected userService = inject(UserService);
  selectedUserRealmControl = new FormControl<string>(
    this.userService.selectedUserRealm(),
    { nonNullable: true, validators: [Validators.required] },
  );
  userFilterControl = new FormControl<string | UserData | null>(
    this.userService.userFilter(),
    { nonNullable: true, validators: [Validators.required] },
  );
  protected tokenService = inject(TokenService);
  selectionContainsAssignedToken = computed(() =>
    this.tokenService
      .tokenSelection()
      .some((token) => token.username && token.username !== ''),
  );
  protected realmService = inject(RealmService);

  constructor(
    public dialogRef: MatDialogRef<
      SelectedUserAssignDialogComponent,
      SelectedUserAssignResult | null
    >,
  ) {}

  togglePinVisibility(): void {
    this.hidePin.update((prev) => !prev);
  }

  onConfirm(): void {
    const realm = this.selectedUserRealmControl.value;
    const userValue = this.userFilterControl.value;
    const user = typeof userValue === 'string' ? null : userValue;

    if (this.pinsMatch() && !!realm && !!user) {
      this.dialogRef.close({
        username: user.username,
        realm,
        pin: this.pin() || null,
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }
}
