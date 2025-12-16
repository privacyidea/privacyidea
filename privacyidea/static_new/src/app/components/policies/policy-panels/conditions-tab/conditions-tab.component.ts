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

import { Component, inject, input, output } from "@angular/core";
import { ConditionsUserComponent } from "./conditions-user/conditions-user.component";
import { ConditionsNodesComponent } from "./conditions-nodes/conditions-nodes.component";
import { ConditionsAdditionalComponent } from "./conditions-additional/conditions-additional.component";
import { PolicyDetail, PolicyService } from "../../../../services/policies/policies.service";
import { ConditionsAdminComponent } from "./conditions-admin/conditions-admin.component";

@Component({
  selector: "app-conditions-tab",
  standalone: true,
  imports: [ConditionsUserComponent, ConditionsNodesComponent, ConditionsAdditionalComponent, ConditionsAdminComponent],
  templateUrl: "./conditions-tab.component.html",
  styleUrl: "./conditions-tab.component.scss"
})
export class ConditionsTabComponent {
  isEditMode = input.required<boolean>();
  policy = input.required<PolicyDetail>();
  policyChange = output<PolicyDetail>();

  onPolicyChange($event: PolicyDetail) {
    this.policyChange.emit($event);
  }
}
