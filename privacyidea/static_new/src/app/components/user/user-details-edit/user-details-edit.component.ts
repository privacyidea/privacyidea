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

import { Component, computed, effect, inject, input, linkedSignal, output, WritableSignal } from "@angular/core";
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

  newUserData: WritableSignal<EditUserData> = linkedSignal(() => {
    let newData: EditUserData = { username: "" };
    const attributes = this.resolverService.userAttributes();
    const initial = this.initialUserData();
    for (const attribute of attributes) {
      newData[attribute] = initial?.[attribute] ?? "";
    }
    return newData;
  });

  attributes = computed(() => {
    const attributes = this.resolverService.userAttributes();
    // Remove 'username' and 'userid' from the list of attributes
    return attributes.filter(attribute => attribute !== "username" && attribute !== "userid");
  });

  attributeColumns = computed(() => {
    const attributes = this.attributes();
    const middle = Math.ceil(attributes.length / 2);
    return [attributes.slice(0, middle), attributes.slice(middle)];
  });

  constructor() {
    effect(() => {
      this.resolverService.selectedResolverName.set(this.resolver());
    });
  }

  updateAttribute(attribute: string, value: string) {
    this.newUserData.set({ ...this.newUserData(), [attribute]: value });
    this.updateData.emit(this.newUserData());
  }
}
