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

import { ResolverService } from "../../../services/resolver/resolver.service";

export interface CreateUserDialogData {
  resolver?: string;
  realm?: string;
}

import { Component, computed, inject, linkedSignal, signal, Signal, WritableSignal } from "@angular/core";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { EditUserData, UserData, UserService } from "../../../services/user/user.service";
import { DialogAction } from "../../../models/dialog";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { UserDetailsEditComponent } from "@components/user/user-details-edit/user-details-edit.component";
import { NotificationService } from "../../../services/notification/notification.service";
import { MatFormField, MatHint, MatLabel, MatError } from "@angular/material/form-field";
import { MatOption, MatSelect } from "@angular/material/select";
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { RealmService } from "../../../services/realm/realm.service";
import { MatInput } from "@angular/material/input";
import { toSignal } from "@angular/core/rxjs-interop";

@Component({
  selector: "app-create-user-dialog",
  imports: [
    DialogWrapperComponent,
    UserDetailsEditComponent,
    MatFormField,
    MatLabel,
    MatOption,
    MatSelect,
    FormsModule,
    MatHint,
    MatError,
    MatInput,
    ReactiveFormsModule
  ],
  templateUrl: "./create-user-dialog.component.html",
  styleUrl: "./create-user-dialog.component.scss"
})
export class CreateUserDialogComponent extends AbstractDialogComponent<CreateUserDialogData, boolean> {
  protected readonly userService = inject(UserService);
  protected readonly resolverService = inject(ResolverService);
  protected readonly realmService = inject(RealmService);
  protected readonly notificationService = inject(NotificationService);

  realm = linkedSignal(() => this.data.realm || this.userService.selectedUserRealm() || "");
  username = new FormControl("", { nonNullable: true, validators: [Validators.required] });
  resolverControl = new FormControl("", { nonNullable: true, validators: [Validators.required] });
  selectedResolver = toSignal(this.resolverControl.valueChanges, { initialValue: this.resolverControl.value });
  inputGroup = new FormGroup({
    username: this.username,
    resolver: this.resolverControl
  });

  inputGroupInvalid = signal(this.inputGroup.invalid);

  constructor() {
    super();
    this.inputGroup.statusChanges.subscribe(() => {
      this.inputGroupInvalid.set(this.inputGroup.invalid);
    });

    // Select initial resolver
    let resolver = this.data.resolver;
    if (!resolver && this.realm()) {
      const realmConfig = this.realmService.realms()[this.realm()];
      resolver = realmConfig?.resolver[0]?.name;
    }
    this.resolverControl.setValue(resolver || "");
  }

  title = $localize`Create New User`;

  dialogActions = linkedSignal(() => {
    return [{
      type: "confirm",
      label: $localize`Create`,
      value: true,
      disabled: this.inputGroupInvalid()
    }] as DialogAction<boolean>[];
  });

  editedUserData: WritableSignal<EditUserData> = linkedSignal(() => {
    return { username: "" };
  });

  correspondingRealms: Signal<string[]> = computed(() => {
    const realms = this.realmService.realms();
    const result: string[] = [];
    for (const [realmName, realmObj] of Object.entries(realms)) {
      if (realmObj.resolver.some(resolver => resolver.name === this.selectedResolver())) {
        result.push(realmName);
      }
    }
    return result;
  });

  create() {
    if (this.inputGroup.invalid) {
      this.inputGroup.markAllAsTouched();
      this.notificationService.openSnackBar($localize`Please fill in all required fields.`);
      return;
    }
    this.editedUserData().username = this.username.value;
    this.userService.createUser(this.resolverControl.value, this.editedUserData()).subscribe({
      next: (success) => {
        if (success) {
          this.userService.usersResource.reload();
          this.dialogRef.close();
        }
      }
    });
  }
}
