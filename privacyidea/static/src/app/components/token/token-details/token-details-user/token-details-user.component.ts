import {Component, effect, Input, signal, Signal, WritableSignal} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from "@angular/forms";
import {MatCell, MatColumnDef, MatRow, MatTableModule} from '@angular/material/table';
import {MatFormField, MatLabel} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatAutocomplete, MatAutocompleteTrigger, MatOption} from '@angular/material/autocomplete';
import {MatSelect} from '@angular/material/select';
import {MatFabButton, MatIconButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {MatDivider} from '@angular/material/divider';
import {TokenService} from '../../../../services/token/token.service';
import {RealmService} from '../../../../services/realm/realm.service';
import {EditButtonsComponent} from '../edit-buttons/edit-buttons.component';
import {UserService} from '../../../../services/user/user.service';

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
    EditButtonsComponent
  ],
  templateUrl: './token-details-user.component.html',
  styleUrl: './token-details-user.component.scss'
})
export class TokenDetailsUserComponent {

  constructor(private tokenService: TokenService, private realmService: RealmService, private userService: UserService) {
    effect(() => {
      if (this.selectedUserRealm()) {
        this.userService.getUsers(this.selectedUserRealm()).subscribe({
          next: (users: any) => {
            console.log('Got users', users);
            this.userOptions.set(users.result.value.map((user: any) => user.username));
          },
          error: error => {
            console.error('Failed to get users', error);
          }
        });
      }
    });

    effect(() => {
      const value = this.selectedUsername();
      const filteredOptions = this._filterUserOptions(value || '');
      this.filteredUserOptions.set(filteredOptions);
    });
  }

  @Input() userData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: WritableSignal<boolean>
  }[]>([]);
  @Input() selectedUsername = signal<string>('');
  @Input() serial!: WritableSignal<string>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isAnyEditing!: Signal<boolean>;
  @Input() realmOptions!: WritableSignal<string[]>;
  userOptions = signal<string[]>([]);
  selectedUserRealm = signal<string>('');
  filteredUserOptions = signal<string[]>([]);

  private _filterUserOptions(value: string): string[] {
    const filterValue = value.toLowerCase();
    return this.userOptions().filter(option => option.toLowerCase().includes(filterValue));
  }

  unassignUser() {
    this.tokenService.unassignUser(this.serial()).subscribe({
      next: () => {
        this.refreshTokenDetails.set(true);
      },
      error: error => {
        console.error('Failed to unassign user', error);
      }
    });
  }

  setPin() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error('PINs do not match');
      return;
    }
    this.tokenService.setPin(this.serial(), this.setPinValue()).subscribe({
      error: error => {
        console.error('Failed to set pin', error);
      }
    });
  }

  setRandomPin() {
    this.tokenService.setRandomPin(this.serial()).subscribe({
      error: error => {
        console.error('Failed to set random pin', error);
      }
    });
  }

  toggleUserEditMode(element: any, type: string = '', action: string = ''): void {
    this.isEditingUser.set(!this.isEditingUser());
    if (this.selectedUserRealm() === '') {
      this.getDefaultRealm();
    }
    if (action === 'save') {
      this.saveUser();
    } else if (action === 'cancel') {
      this.selectedUsername.set('');
    }
  }

  saveUser() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error('PINs do not match');
      return;
    }
    this.tokenService.assignUser(this.serial(), this.selectedUsername(), this.selectedUserRealm(), this.setPinValue()).subscribe({
      next: () => {
        this.setPinValue.set('');
        this.repeatPinValue.set('');
        this.selectedUsername.set('');
        this.selectedUserRealm.set('');
        this.refreshTokenDetails.set(true)
      },
      error: error => {
        console.error('Failed to assign user', error);
      }
    });
  }

  private getDefaultRealm() {
    this.realmService.getDefaultRealm().subscribe({
      next: (realm: any) => {
        this.selectedUserRealm.set(Object.keys(realm.result.value)[0]);
      },
      error: error => {
        console.error('Failed to get default realm', error);
      }
    });
  }
}
