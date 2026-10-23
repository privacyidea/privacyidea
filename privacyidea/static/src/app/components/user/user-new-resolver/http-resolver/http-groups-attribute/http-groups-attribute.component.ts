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

import { Component, computed, input } from "@angular/core";
import { disabled, FieldTree, FormField, SchemaPathTree } from "@angular/forms/signals";
import { MatFormField, MatHint } from "@angular/material/form-field";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTooltip } from "@angular/material/tooltip";

export interface UserGroupsModel {
  active: boolean;
  pi_user_groups_key: string;
  user_groups_attribute: string;
  method: string;
  endpoint: string;
}

/**
 * Rules of the user groups form: the groups fields are disabled while the groups retrieval is not active.
 */
export function userGroupsRules(path: SchemaPathTree<UserGroupsModel>): void {
  for (const field of [path.pi_user_groups_key, path.user_groups_attribute, path.method, path.endpoint]) {
    disabled(field, (ctx) => !ctx.valueOf(path.active));
  }
}

@Component({
  selector: "app-http-groups-attribute",
  imports: [FormField, MatFormField, MatHint, MatInput, MatLabel, MatOption, MatSelect, MatSlideToggle, MatTooltip],
  templateUrl: "./http-groups-attribute.component.html",
  styleUrl: "./http-groups-attribute.component.scss"
})
export class HttpGroupsAttributeComponent {
  /** The slice of the parent form this component edits. */
  field = input.required<FieldTree<UserGroupsModel>>();
  readonly slideToggleTooltipSignal = computed(() =>
    this.field().active().value()
      ? $localize`:@@resolver.disableUserGroups:Disable user groups retrieval`
      : $localize`:@@resolver.enableUserGroups:Enable user groups retrieval`
  );
  resolverType = input.required<string>();
}
