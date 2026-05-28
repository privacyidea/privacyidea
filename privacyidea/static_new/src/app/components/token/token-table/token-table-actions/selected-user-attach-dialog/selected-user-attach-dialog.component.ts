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
import { Component, computed, inject, signal, WritableSignal } from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatError, MatFormField, MatLabel, MatSuffix } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserData, UserService, UserServiceInterface } from "@services/user/user.service";

export interface SelectedUserAssignResult {
  username: string;
  realm: string;
  pin?: string | null;
}

@Component({
  selector: "app-selected-user-attach-dialog",
  imports: [
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatError,
    MatFormField,
    MatLabel,
    MatSelect,
    MatOption,
    MatInput,
    MatIcon,
    MatButtonModule,
    MatSuffix,
    ClearableInputComponent,
    DialogWrapperComponent
  ],
  templateUrl: "./selected-user-attach-dialog.component.html",
  styleUrl: "./selected-user-attach-dialog.component.scss"
})
export class SelectedUserAssignDialogComponent extends AbstractDialogComponent<any, SelectedUserAssignResult | null> {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  pin: WritableSignal<string> = signal("");
  pinRepeat: WritableSignal<string> = signal("");
  hidePin: WritableSignal<boolean> = signal(true);
  selectedRealm = signal(this.userService.selectedUserRealm());
  selectedUser = signal<UserData | null>(null);
  userFilter = signal(this.userService.selectionFilter());
  pinsMatch = computed(() => this.pin() === this.pinRepeat());
  readonly realmInvalid = computed(() => !this.selectedRealm());
  readonly userInvalid = computed(() => !this.selectedUser());
  selectionContainsAssignedToken = computed(() =>
    this.tokenService.tokenSelection().some((token) => token.username && token.username !== "")
  );
  readonly actions = computed<DialogAction<"submit" | null>[]>(() => [
    {
      label: $localize`Assign to Selected Token`,
      value: "submit",
      type: "confirm",
      className: "input-width-m",
      primary: true,
      disabled: !this.pinsMatch() || this.realmInvalid() || this.userInvalid()
    }
  ]);

  onRealmChange(realm: string): void {
    this.selectedRealm.set(realm);
    this.userService.selectedUserRealm.set(realm);
    this.selectedUser.set(null);
    this.userFilter.set("");
    this.userService.selectionFilter.set("");
  }

  onUserFilterInput(value: string): void {
    this.userFilter.set(value);
    this.userService.selectionFilter.set(value);
    if (!value) {
      this.selectedUser.set(null);
    }
  }

  onUserSelected(user: UserData): void {
    this.selectedUser.set(user);
    this.userFilter.set(user.username);
    this.userService.selectionFilter.set(user.username);
  }

  displayUser = (value: UserData | string | null): string => {
    if (!value) return "";
    if (typeof value === "string") return value;
    return value.username;
  };

  togglePinVisibility(): void {
    this.hidePin.update((prev) => !prev);
  }

  onConfirm(): void {
    const realm = this.selectedRealm();
    const user = this.selectedUser();

    if (this.pinsMatch() && !!realm && !!user) {
      this.dialogRef.close({
        username: user.username,
        realm,
        pin: this.pin() || null
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }

  onAction(value: "submit" | null): void {
    if (value === "submit") {
      this.onConfirm();
    } else {
      this.onCancel();
    }
  }
}
