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
import { Component, computed, effect, inject, input, signal } from "@angular/core";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatError, MatFormField, MatHint } from "@angular/material/form-field";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatSelect } from "@angular/material/select";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { UserData, UserService, UserServiceInterface } from "@services/user/user.service";

@Component({
  selector: "app-user-assignment",
  templateUrl: "./user-assignment.component.html",
  styleUrls: ["./user-assignment.component.scss"],
  standalone: true,
  imports: [
    ClearableInputComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatCheckbox,
    MatError,
    MatHint
  ]
})
export class UserAssignmentComponent {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);

  showOnlyAddToRealm = input<boolean>(false);
  required = input<boolean>(false);

  onlyAddToRealm = signal(false);
  userFilter = signal<string>(this.userService.selectionUsernameFilter());

  readonly userInputDisabled = computed(() => !this.userService.selectedUserRealm() || this.onlyAddToRealm());

  readonly displayUser = (value: UserData | string | null): string => {
    if (!value) return "";
    if (typeof value === "string") return value;
    return value.username;
  };

  constructor() {
    effect(() => {
      const users = this.userService.selectionFilteredUsers();
      const filter = this.userFilter();
      if (users.length === 1 && filter === users[0].username) {
        this.userService.selectionFilter.set(users[0]);
      }
    });
  }

  onlyAddToRealmChange(checked: boolean) {
    this.onlyAddToRealm.set(checked);
    if (checked) {
      this.clearUser();
    }
  }

  onSelectedRealmChange(realm: string) {
    this.userService.selectedUserRealm.set(realm);
    this.clearUser();
  }

  onUserFilterInput(value: string): void {
    this.userFilter.set(value);
    this.userService.selectionFilter.set(value);
    if (value) {
      this.onlyAddToRealm.set(false);
    }
  }

  onUserSelected(user: UserData): void {
    this.userFilter.set(user.username);
    this.userService.selectionFilter.set(user);
    this.onlyAddToRealm.set(false);
  }

  clearUser(): void {
    this.userFilter.set("");
    this.userService.selectionFilter.set("");
  }
}
