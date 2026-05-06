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
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatButtonModule } from "@angular/material/button";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { RealmService, RealmServiceInterface } from "../../../../../services/realm/realm.service";
import { TokenService, TokenServiceInterface } from "../../../../../services/token/token.service";
import { UserData, UserService, UserServiceInterface } from "../../../../../services/user/user.service";
import { ClearableInputComponent } from "../../../../shared/clearable-input/clearable-input.component";
import { AuthService, AuthServiceInterface } from "../../../../../services/auth/auth.service";
import { AbstractDialogComponent } from "../../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "../../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "../../../../../models/dialog";
import { toSignal } from "@angular/core/rxjs-interop";
import { map, startWith } from "rxjs";

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
    MatButtonModule,
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
  private readonly realmInvalid = toSignal(
    this.selectedUserRealmControl.statusChanges.pipe(
      startWith(this.selectedUserRealmControl.status),
      map(() => this.selectedUserRealmControl.invalid)
    ),
    { initialValue: this.selectedUserRealmControl.invalid }
  );
  private readonly userInvalid = toSignal(
    this.userFilterControl.statusChanges.pipe(
      startWith(this.userFilterControl.status),
      map(() => this.userFilterControl.invalid)
    ),
    { initialValue: this.userFilterControl.invalid }
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

  onAction(value: "submit" | null): void {
    if (value === "submit") {
      this.onConfirm();
    } else {
      this.onCancel();
    }
  }
}
