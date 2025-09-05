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
import { Component, computed, inject, signal, WritableSignal } from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatDialogActions, MatDialogContent, MatDialogRef, MatDialogTitle } from "@angular/material/dialog";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { RealmService, RealmServiceInterface } from "../../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../../services/token/token.service";
import { UserData, UserService, UserServiceInterface } from "../../../../services/user/user.service";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";
import { AuthService, AuthServiceInterface } from "../../../../services/auth/auth.service";

export interface SelectedUserAssignResult {
  username: string;
  realm: string;
  pin?: string | null;
}

@Component({
  selector: "app-selected-user-attach-dialog",
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
    ClearableInputComponent
  ],
  templateUrl: "./selected-user-attach-dialog.component.html",
  styleUrl: "./selected-user-attach-dialog.component.scss"
})
export class SelectedUserAssignDialogComponent {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly dialogRef: MatDialogRef<SelectedUserAssignDialogComponent, SelectedUserAssignResult | null> =
    inject(MatDialogRef);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  pin: WritableSignal<string> = signal("");
  pinRepeat: WritableSignal<string> = signal("");
  hidePin: WritableSignal<boolean> = signal(true);
  pinsMatch = computed(() => this.pin() === this.pinRepeat());
  selectedUserRealmControl = new FormControl<string>(this.userService.selectedUserRealm(), {
    nonNullable: true,
    validators: [Validators.required]
  });
  userFilterControl = new FormControl<string | UserData | null>(this.userService.selectionFilter(), {
    nonNullable: true,
    validators: [Validators.required]
  });
  selectionContainsAssignedToken = computed(() =>
    this.tokenService.tokenSelection().some((token) => token.username && token.username !== "")
  );

  ngOnInit(): void {
    this.selectedUserRealmControl.valueChanges.subscribe((value) => {
      if (value !== this.userService.selectedUserRealm()) {
        this.userService.selectedUserRealm.set(value ?? "");
      }
    });
  }

  togglePinVisibility(): void {
    this.hidePin.update((prev) => !prev);
  }

  onConfirm(): void {
    const realm = this.selectedUserRealmControl.value;
    const userValue = this.userFilterControl.value;
    const user = typeof userValue === "string" ? null : userValue;

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
}
