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
import { Component, computed, inject, signal } from "@angular/core";
import { applyWhen, form, FormField, required, validate } from "@angular/forms/signals";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { MaskedInputComponent } from "@components/shared/masked-input/masked-input.component";
import { DialogAction } from "@models/dialog";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserData, UserService, UserServiceInterface } from "@services/user/user.service";
import { ERR, markRequired, mustEqual } from "@utils/form-rules.utils";
import { blurErrorStateMatcher, clearField, hasError, touchAll } from "@utils/form-state.utils";

export interface SelectedUserAssignResult {
  username: string;
  realm: string;
  pin?: string | null;
}

@Component({
  selector: "app-selected-user-attach-dialog",
  imports: [
    FormField,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatError,
    MatFormField,
    MatLabel,
    MatSelect,
    MatOption,
    MatInput,
    ClearableInputComponent,
    DialogWrapperComponent,
    MaskedInputComponent
  ],
  templateUrl: "./selected-user-attach-dialog.component.html",
  styleUrl: "./selected-user-attach-dialog.component.scss"
})
export class SelectedUserAssignDialogComponent extends AbstractDialogComponent<
  undefined,
  SelectedUserAssignResult | null
> {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly hasError = hasError;
  protected readonly ERR = ERR;

  // The user text is the autocomplete input. A user counts as chosen only through `selectedUser`.
  readonly model = signal({
    realm: this.userService.selectedUserRealm(),
    userText: this.userService.selectionUsernameFilter(),
    pin: "",
    pinRepeat: ""
  });
  selectedUser = signal<UserData | null>(null);
  readonly userFocused = signal(false);
  readonly userErrorMatcher = blurErrorStateMatcher(this.userFocused);
  readonly form = form(this.model, (f) => {
    required(f.realm);
    markRequired(f.userText);
    validate(f.userText, () => (this.selectedUser() ? [] : [{ kind: ERR.required }]));
    // The PIN fields only exist when setting a PIN is allowed, so only then can they mismatch.
    applyWhen(
      f,
      () => this.authService.actionAllowed("setpin"),
      (p) => mustEqual(p.pinRepeat, () => this.model().pin)
    );
  });
  readonly pinMismatchError = computed(() =>
    hasError(this.form.pinRepeat, ERR.pinMismatch) ? $localize`:@@common.pinsDoNotMatch:PINs do not match` : ""
  );
  readonly actions = computed<DialogAction<"submit" | null>[]>(() => [
    {
      label: $localize`:@@token.assignSelected:Assign to Selected Token`,
      value: "submit",
      type: "confirm",
      className: "input-width-m",
      primary: true,
      disabled: !this.form().valid()
    }
  ]);
  selectionContainsAssignedToken = computed(() =>
    this.tokenService.tokenSelection.selectedRows().some((token) => token.username && token.username !== "")
  );

  onRealmChange(): void {
    this.userService.selectedUserRealm.set(this.model().realm);
    this.selectedUser.set(null);
    clearField(this.form.userText, "");
    this.userService.selectionFilter.set("");
  }

  onUserFilterInput(value: string): void {
    this.userService.selectionFilter.set(value);
    if (!value) {
      this.selectedUser.set(null);
    }
  }

  clearUser(): void {
    clearField(this.form.userText, "");
    this.onUserFilterInput("");
  }

  onUserSelected(username: string): void {
    const user = this.userService.selectionFilteredUsers().find((candidate) => candidate.username === username);
    this.selectedUser.set(user ?? null);
    this.userService.selectionFilter.set(username);
  }

  onConfirm(): void {
    const user = this.selectedUser();
    if (!this.form().valid() || !user) {
      void touchAll(this.form);
      return;
    }
    this.dialogRef.close({
      username: user.username,
      realm: this.model().realm,
      pin: this.model().pin || null
    });
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
