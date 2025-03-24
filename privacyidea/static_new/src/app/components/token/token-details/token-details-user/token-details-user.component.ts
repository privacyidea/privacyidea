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
import { EditButtonsComponent } from '../../../shared/edit-buttons/edit-buttons.component';
import { UserService } from '../../../../services/user/user.service';
import { NgClass } from '@angular/common';
import { OverflowService } from '../../../../services/overflow/overflow.service';
import { NotificationService } from '../../../../services/notification/notification.service';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { distinctUntilChanged, from, switchMap } from 'rxjs';
import { map } from 'rxjs/operators';

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
  @Input() userData = signal<
    {
      value: any;
      keyMap: { label: string; key: string };
      isEditing: WritableSignal<boolean>;
    }[]
  >([]);
  @Input() selectedUsername = signal<string>('');
  @Input() tokenSerial!: WritableSignal<string>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isAnyEditingOrRevoked!: Signal<boolean>;
  @Input() realmOptions!: WritableSignal<string[]>;
  selectedUserRealm = signal<string>('');
  fetchedUsernames = toSignal(
    toObservable(this.selectedUserRealm).pipe(
      distinctUntilChanged(),
      switchMap((realm) => {
        if (!realm) {
          return from<string[]>([]);
        }
        return this.userService
          .getUsers(realm)
          .pipe(
            map((result: any) =>
              result.value.map((user: any) => user.username),
            ),
          );
      }),
    ),
    { initialValue: [] },
  );
  userOptions = computed(() => this.fetchedUsernames());
  filteredUserOptions = computed(() => {
    const filterValue = (this.selectedUsername() || '').toLowerCase();
    return this.userOptions().filter((option: any) =>
      option.toLowerCase().includes(filterValue),
    );
  });

  constructor(
    private tokenService: TokenService,
    private realmService: RealmService,
    private userService: UserService,
    private notificationService: NotificationService,
    protected overflowService: OverflowService,
  ) {}

  unassignUser() {
    this.tokenService.unassignUser(this.tokenSerial()).subscribe({
      next: () => {
        this.refreshTokenDetails.set(true);
      },
    });
  }

  setPin() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error('PINs do not match.');
      this.notificationService.openSnackBar('PINs do not match.');
      return;
    }
    this.tokenService.setPin(this.tokenSerial(), this.setPinValue());
  }

  setRandomPin() {
    this.tokenService.setRandomPin(this.tokenSerial());
  }

  toggleUserEditMode(
    element: any,
    type: string = '',
    action: string = '',
  ): void {
    this.isEditingUser.set(!this.isEditingUser());
    if (this.selectedUserRealm() === '') {
      this.realmService.getDefaultRealm().subscribe({
        next: (realm: any) => {
          this.selectedUserRealm.set(realm);
        },
      });
    }
    if (action === 'save') {
      this.saveUser();
    } else if (action === 'cancel') {
      this.selectedUsername.set('');
    }
  }

  saveUser() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error('PINs do not match.');
      this.notificationService.openSnackBar('PINs do not match.');
      return;
    }
    this.tokenService
      .assignUser(
        this.tokenSerial(),
        this.selectedUsername(),
        this.selectedUserRealm(),
        this.setPinValue(),
      )
      .subscribe({
        next: () => {
          this.setPinValue.set('');
          this.repeatPinValue.set('');
          this.selectedUsername.set('');
          this.selectedUserRealm.set('');
          this.refreshTokenDetails.set(true);
        },
      });
  }
}
