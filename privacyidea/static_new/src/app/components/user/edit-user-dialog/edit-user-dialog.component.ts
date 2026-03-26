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

import { Component, computed, effect, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { EditUserData, UserData, UserService } from "../../../services/user/user.service";
import { DialogAction } from "../../../models/dialog";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { UserDetailsEditComponent } from "@components/user/user-details-edit/user-details-edit.component";
import { PendingChangesDialogComponent } from "@components/shared/dialog/abstract-dialog/pending-changes-dialog.component";
import { ROUTE_PATHS } from "../../../route_paths";
import { ContentService } from "../../../services/content/content.service";
import { NAVIGATION_ACCESSIBLE_DIALOG_CLASS } from "../../../constants/global.constants";

@Component({
  selector: "app-edit-user-dialog",
  standalone: true,
  host: {
    class: NAVIGATION_ACCESSIBLE_DIALOG_CLASS
  },
  imports: [DialogWrapperComponent, UserDetailsEditComponent],
  templateUrl: "./edit-user-dialog.component.html",
  styleUrl: "./edit-user-dialog.component.scss"
})
export class EditUserDialogComponent extends PendingChangesDialogComponent<UserData, boolean> {
  protected readonly userService = inject(UserService);
  protected readonly contentService = inject(ContentService);

  username = computed(() => this.data.username);
  title = computed(() => $localize`Edit User` + (this.username() ? ": " + this.username() : ""));
  dialogActions = linkedSignal(() => {
    return [
      {
        type: "confirm",
        label: $localize`Save`,
        value: true
      }
    ] as DialogAction<boolean>[];
  });
  editedUserData: WritableSignal<EditUserData> = linkedSignal(() => {
    if (this.data) {
      return this.data;
    }
    return { username: this.username() || "" };
  });

  canSave = signal(true);
  isDirty = computed(() => this.editedUserData() !== this.data);

  constructor() {
    super();

    effect(() => {
      if (this.contentService.routeUrl() !== ROUTE_PATHS.USERS_DETAILS + "/" + this.username()) {
        this.dialogRef?.close(true);
      }
    });
  }

  onUpdateUserData(newData: EditUserData): void {
    this.editedUserData.set(newData);
  }

  override async onSave(): Promise<boolean> {
    this.editedUserData().username = this.username();
    return new Promise((resolve) => {
      this.userService.editUser(this.data.resolver, this.editedUserData()).subscribe({
        next: (success) => {
          if (success) {
            this.userService.userResource.reload();
            resolve(true);
          } else {
            resolve(false);
          }
        },
        error: () => resolve(false)
      });
    });
  }

  save() {
    this.editedUserData().username = this.username();
    this.userService.editUser(this.data.resolver, this.editedUserData()).subscribe({
      next: (success) => {
        if (success) {
          this.userService.userResource.reload();
          this.dialogRef.close();
        }
      }
    });
  }
}
