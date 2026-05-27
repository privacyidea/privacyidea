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

import { Component, computed, Input, WritableSignal } from "@angular/core";
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

@Component({
  selector: "app-http-groups-attribute",
  imports: [
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatSlideToggle,
    MatTooltip
  ],
  templateUrl: "./http-groups-attribute.component.html",
  styleUrl: "./http-groups-attribute.component.scss"
})
export class HttpGroupsAttributeComponent {
  @Input({ required: true }) model!: WritableSignal<UserGroupsModel>;
  @Input({ required: true }) resolverType!: string;

  readonly slideToggleTooltipSignal = computed(() =>
    this.model().active ? $localize`Disable user groups retrieval` : $localize`Enable user groups retrieval`
  );
}
