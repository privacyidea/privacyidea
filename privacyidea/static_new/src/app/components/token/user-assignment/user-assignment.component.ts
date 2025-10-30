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
import { Component, Input, inject, effect } from "@angular/core";
import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { FormControl, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger, MatOption } from "@angular/material/autocomplete";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatError, MatFormField, MatHint } from "@angular/material/form-field";
import { MatSelect } from "@angular/material/select";
import { UserData, UserService, UserServiceInterface } from "../../../services/user/user.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { MatCheckbox } from "@angular/material/checkbox";

@Component({
  selector: "app-user-assignment",
  templateUrl: "./user-assignment.component.html",
  styleUrls: ["./user-assignment.component.scss"],
  standalone: true,
  imports: [
    ClearableInputComponent,
    FormsModule,
    MatAutocomplete,
    MatAutocompleteTrigger,
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    ReactiveFormsModule,
    MatCheckbox,
    MatError,
    MatHint
  ]
})
export class UserAssignmentComponent {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);

  @Input() selectedUserRealmControl?: FormControl<string>;
  @Input() userFilterControl?: FormControl<string | UserData | null>;
  @Input() onlyAddToRealmControl?: FormControl<boolean>;
  @Input() showOnlyAddToRealm?: boolean;

  // Internal defaults if not provided
  internalSelectedUserRealmControl = new FormControl<string>(this.userService.selectedUserRealm(), { nonNullable: true });
  internalUserFilterControl = new FormControl<string | UserData | null>(this.userService.selectionFilter(), { nonNullable: true });
  internalOnlyAddToRealmControl = new FormControl<boolean>(false, { nonNullable: true });

  get selectedUserRealmCtrl() {
    return this.selectedUserRealmControl ?? this.internalSelectedUserRealmControl;
  }
  get userFilterCtrl() {
    return this.userFilterControl ?? this.internalUserFilterControl;
  }
  get onlyAddToRealmCtrl() {
    return this.onlyAddToRealmControl ?? this.internalOnlyAddToRealmControl;
  }

  constructor() {
    effect(() => {
      const users = this.userService.selectionFilteredUsers();
      if (users.length === 1 && this.userFilterCtrl.value === users[0].username) {
        this.userFilterCtrl.setValue(users[0]);
      }
    });
  }

  ngOnInit(): void {
    this.userFilterCtrl.valueChanges.subscribe((value) => {
      this.userService.selectionFilter.set(value ?? "");
      if (value) {
        this.onlyAddToRealmCtrl.setValue(false, {});
        this.onlyAddToRealmCtrl.disable({ emitEvent: false });
      } else {
        this.onlyAddToRealmCtrl.enable({ emitEvent: false });
      }
    });
    this.selectedUserRealmCtrl.valueChanges.subscribe((value) => {
      this.userFilterCtrl.reset("", { emitEvent: false });
      if (!value) {
        this.userFilterCtrl.disable({ emitEvent: false });
      } else {
        this.userFilterCtrl.enable({ emitEvent: false });
      }

      if (value !== this.userService.selectedUserRealm()) {
        this.userService.selectedUserRealm.set(value ?? "");
      }
    });
    this.onlyAddToRealmCtrl.valueChanges.subscribe((value) => {
      if (value) {
        this.userFilterCtrl.disable({ emitEvent: false });
      } else {
        this.userFilterCtrl.enable({ emitEvent: false });
      }
    });
  }
}
