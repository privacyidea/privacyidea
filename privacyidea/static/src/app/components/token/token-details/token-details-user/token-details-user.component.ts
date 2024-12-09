import {Component, Input, Signal, signal, WritableSignal, effect} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from "@angular/forms";
import {
  MatCell, MatCellDef,
  MatColumnDef,
  MatHeaderCell, MatHeaderCellDef,
  MatRow,
  MatRowDef,
  MatTable
} from '@angular/material/table';
import {MatFormField, MatLabel} from '@angular/material/form-field';
import {MatInput} from '@angular/material/input';
import {MatAutocomplete, MatAutocompleteTrigger, MatOption} from '@angular/material/autocomplete';
import {MatSelect} from '@angular/material/select';
import {MatFabButton, MatIconButton} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';
import {MatDivider} from '@angular/material/divider';
import {TokenService} from '../../../../services/token/token.service';
import {AsyncPipe} from '@angular/common';
import {Observable} from 'rxjs';
import {RealmService} from '../../../../services/realm/realm.service';
import {EditButtonsComponent} from '../edit-buttons/edit-buttons.component';

@Component({
  selector: 'app-token-details-user',
  standalone: true,
  imports: [
    MatTable,
    MatColumnDef,
    MatHeaderCell,
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
    MatRowDef,
    MatHeaderCellDef,
    MatCellDef,
    EditButtonsComponent
  ],
  templateUrl: './token-details-user.component.html',
  styleUrl: './token-details-user.component.css'
})
export class TokenDetailsUserComponent {

  constructor(private tokenService: TokenService, private realmService: RealmService) {
  }

  @Input() userData = signal<{
    value: any;
    keyMap: { label: string; key: string },
    isEditing: WritableSignal<boolean>
  }[]>([]);
  @Input() selectedUsername = new FormControl<string>('');
  @Input() selectedUserRealm!: WritableSignal<string>;
  @Input() serial!: WritableSignal<string>;
  @Input() refreshTokenDetails!: WritableSignal<boolean>;
  @Input() setPinValue!: WritableSignal<string>;
  @Input() repeatPinValue!: WritableSignal<string>;
  @Input() isEditingUser!: WritableSignal<boolean>;
  @Input() isEditingInfo!: WritableSignal<boolean>;
  @Input() isAnyEditing!: Signal<boolean>;
  @Input() realmOptions!: WritableSignal<string[]>;
  @Input() filteredUserOptions!: WritableSignal<string[]>;

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
      this.selectedUsername.reset();
    }
  }

  saveUser() {
    if (this.setPinValue() !== this.repeatPinValue()) {
      console.error('PINs do not match');
      return;
    }
    this.tokenService.assignUser(this.serial(), this.selectedUsername.value, this.selectedUserRealm(), this.setPinValue()).subscribe({
      next: () => {
        this.setPinValue.set('');
        this.repeatPinValue.set('');
        this.selectedUsername.reset();
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
