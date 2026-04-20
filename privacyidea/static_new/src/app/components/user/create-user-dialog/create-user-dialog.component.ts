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
import { Component, computed, effect, inject, linkedSignal, signal, Signal, WritableSignal } from "@angular/core";
import { EditUserData, UserService } from "../../../services/user/user.service";
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
import { ROUTE_PATHS } from "../../../route_paths";
import { ContentService } from "../../../services/content/content.service";
import { PendingChangesDialogComponent } from "@components/shared/dialog/abstract-dialog/pending-changes-dialog.component";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "../../../constants/global.constants";

export interface CreateUserDialogData {
  resolver?: string;
  realm?: string;
}

@Component({
  selector: "app-create-user-dialog",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
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
export class CreateUserDialogComponent extends PendingChangesDialogComponent<CreateUserDialogData, boolean> {
  protected readonly userService = inject(UserService);
  protected readonly resolverService = inject(ResolverService);
  protected readonly realmService = inject(RealmService);
  protected readonly notificationService = inject(NotificationService);
  private readonly contentService = inject(ContentService);

  realm = linkedSignal(() => this.data.realm || this.userService.selectedUserRealm() || "");
  username = new FormControl("", { nonNullable: true, validators: [Validators.required] });
  resolverControl = new FormControl("", { nonNullable: true, validators: [Validators.required] });
  selectedResolver = toSignal(this.resolverControl.valueChanges, { initialValue: this.resolverControl.value });
  inputGroup = new FormGroup({
    username: this.username,
    resolver: this.resolverControl
  });

  canSave = signal(this.inputGroup.valid);
  inputGroupPristine = signal(this.inputGroup.pristine);
  isDirty = computed(() => {
    return !this.inputGroupPristine() || !this.editUserDataIsEmpty();
  });

  constructor() {
    super();
    this.inputGroup.statusChanges.subscribe(() => {
      this.canSave.set(this.inputGroup.valid);
      this.inputGroupPristine.set(this.inputGroup.pristine);
    });
    this.inputGroup.valueChanges.subscribe(() => {
      this.inputGroupPristine.set(this.inputGroup.pristine);
    });

    // Select initial resolver
    let resolver = this.data.resolver;
    if (!resolver && this.realm()) {
      const realmConfig = this.realmService.realms()[this.realm()];
      resolver = realmConfig?.resolver[0]?.name;
    }
    this.resolverControl.setValue(resolver || "");

    // Close the dialog when navigating away from the events route
    // However, changing the route is disabled via the pendingChangesGuard when there are unsaved changes. This effect
    // will only be triggered when there are no unsaved changes or when the user confirmed discarding them.
    effect(() => {
      if (this.contentService.routeUrl() !== ROUTE_PATHS.USERS) {
        this.dialogRef?.close(true);
      }
    });
  }

  title = $localize`Create New User`;

  dialogActions = linkedSignal(() => {
    return [
      {
        type: "confirm",
        label: $localize`Create`,
        value: true,
        primary: true,
        disabled: !this.canSave()
      }
    ] as DialogAction<boolean>[];
  });

  editedUserData: WritableSignal<EditUserData> = linkedSignal(() => {
    return { username: "" };
  });

  editUserDataIsEmpty = computed(() => {
    return Object.values(this.editedUserData()).every((value) => value === "" || value === undefined);
  });

  correspondingRealms: Signal<string[]> = computed(() => {
    const realms = this.realmService.realms();
    const result: string[] = [];
    for (const [realmName, realmObj] of Object.entries(realms)) {
      if (realmObj.resolver.some((resolver) => resolver.name === this.selectedResolver())) {
        result.push(realmName);
      }
    }
    return result;
  });

  override async onSave(): Promise<boolean> {
    this.editedUserData().username = this.username.value;
    return new Promise((resolve) => {
      this.userService.createUser(this.resolverControl.value, this.editedUserData()).subscribe({
        next: (success) => {
          if (success) {
            this.userService.usersResource.reload();
            this.dialogRef.close();
            resolve(true);
          } else {
            resolve(false);
          }
        },
        error: () => resolve(false)
      });
    });
  }

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
