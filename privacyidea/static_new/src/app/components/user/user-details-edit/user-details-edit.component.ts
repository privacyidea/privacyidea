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

import {Component, computed, effect, inject, input, linkedSignal, output, signal, WritableSignal} from "@angular/core";
import { EditUserData, UserData } from "../../../services/user/user.service";
import { ResolverService, ResolverServiceInterface } from "../../../services/resolver/resolver.service";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";

@Component({
  selector: "app-user-details-edit",
  imports: [
    MatFormField,
    MatInput,
    MatLabel
  ],
  templateUrl: "./user-details-edit.component.html",
  styleUrl: "./user-details-edit.component.scss"
})
export class UserDetailsEditComponent {
  protected readonly resolverService: ResolverServiceInterface = inject(ResolverService);

  resolver = input.required<string>();
  initialUserData = input<UserData>();
  updateData = output<EditUserData>();

  // Store the latest user data to preserve edits
  private lastUserData: WritableSignal<EditUserData | null> = signal(null);

  protected newUserData: WritableSignal<EditUserData> = linkedSignal(() => {
    const attributes = this.resolverService.userAttributes();
    const previousData = this.lastUserData() || this.initialUserData();
    let newData: EditUserData = { username: previousData?.username || "" };
    for (const attribute of attributes) {
      // Preserve existing value for attributes that remain, else initialize with empty string
      newData[attribute] = previousData?.[attribute] ?? "";
    }
    return newData;
  });

  attributes = computed(() => {
    const attributes = this.resolverService.userAttributes();
    // Remove 'username' and 'userid' from the list of attributes
    return attributes.filter(attribute => attribute !== "username" && attribute !== "userid");
  });

  constructor() {
    effect(() => {
      this.resolverService.selectedResolverName.set(this.resolver());
    });
  }

  setNewUserData(attribute: string, value: string) {
    const updated = { ...this.newUserData(), [attribute]: value };
    this.newUserData.set(updated);
    this.lastUserData.set(updated);
    this.updateData.emit(this.newUserData());
  }
}
