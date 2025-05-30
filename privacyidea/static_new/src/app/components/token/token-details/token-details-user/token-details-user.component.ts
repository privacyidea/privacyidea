import {
  Component,
  computed,
  Input,
  signal,
  Signal,
  WritableSignal,
} from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  MatCell,
  MatColumnDef,
  MatRow,
  MatTableModule,
} from '@angular/material/table';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import {
  MatAutocomplete,
  MatAutocompleteTrigger,
  MatOption,
} from '@angular/material/autocomplete';
import { MatSelect } from '@angular/material/select';
import { MatFabButton, MatIconButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatDivider } from '@angular/material/divider';
import { TokenService } from '../../../../services/token/token.service';
import { RealmService } from '../../../../services/realm/realm.service';
import {
  EditableElement,
  EditButtonsComponent,
} from '../../../shared/edit-buttons/edit-buttons.component';
import { UserService } from '../../../../services/user/user.service';
import { NgClass } from '@angular/common';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { NotificationService } from '../../../../services/notification/notification.service';

@Component({
  selector: 'app-token-details-user',
  standalone: true,
  imports: [
    MatTableModule,
    MatColumnDef,
    MatCell,
    MatFormField,
    MatInput,
    ReactiveFormsModule,
    MatAutocompleteTrigger,
    MatAutocomplete,
    MatOption,
    FormsModule,
    MatSelect,
    MatIconButton,
    MatIcon,
    MatDivider,
    MatFabButton,
    MatRow,
    MatLabel,
    EditButtonsComponent,
    NgClass,
  ],
  templateUrl: './token-details-user.component.html',
  styleUrl: './token-details-user.component.scss',
})
export class TokenDetailsUserComponent {
  @Input() userData = signal<EditableElement[]>([]);
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isAnyEditingOrRevoked!: Signal<boolean>;
  tokenType = computed(() => {
    const tokenDetail = this.tokenService.tokenDetailResource.value();
    return tokenDetail?.result?.value?.tokens?.[0].tokentype;
  });

  constructor(
    protected tokenService: TokenService,
    protected realmService: RealmService,
    protected userService: UserService,
    private notificationService: NotificationService,
    protected overflowService: OverflowService,
  ) {}

  unassignUser() {
    this.tokenService.unassignUser(this.tokenSerial()).subscribe({
      next: () => {
        this.tokenService.tokenDetailResource.reload();
      },
    });
  }

  setPin() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error('PINs do not match.');
      this.notificationService.openSnackBar('PINs do not match.');
      return;
    }
    this.tokenService.setPin(this.tokenSerial(), this.setPinValue()).subscribe({
      next: () => {
        this.notificationService.openSnackBar('PIN set successfully.');
      },
    });
  }

  setRandomPin() {
    this.tokenService.setRandomPin(this.tokenSerial()).subscribe({
      next: () => {
        this.notificationService.openSnackBar('PIN set successfully.');
      },
    });
  }

  toggleUserEdit(): void {
    this.isEditingUser.update((b) => !b);
    this.realmService.defaultRealmResource.reload();
  }

  cancelUserEdit(): void {
    this.isEditingUser.update((b) => !b);
    this.userService.selectedUsername.set('');
  }

  saveUser() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error('PINs do not match.');
      this.notificationService.openSnackBar('PINs do not match.');
      return;
    }
    this.tokenService
      .assignUser({
        tokenSerial: this.tokenSerial(),
        username: this.userService.selectedUsername(),
        realm: this.userService.selectedUserRealm(),
        pin: this.setPinValue(),
      })
      .subscribe({
        next: () => {
          this.setPinValue.set('');
          this.repeatPinValue.set('');
          this.userService.selectedUsername.set('');
          this.userService.selectedUserRealm.set('');
          this.isEditingUser.update((b) => !b);
          this.tokenService.tokenDetailResource.reload();
        },
      });
  }
}
