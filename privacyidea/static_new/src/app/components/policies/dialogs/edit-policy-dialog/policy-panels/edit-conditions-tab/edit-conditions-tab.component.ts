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

import { Component, inject, input, output, computed } from "@angular/core";
import {
  PolicyServiceInterface,
  PolicyService,
  PolicyDetail
} from "../../../../../../services/policies/policies.service";
import { EditAdditionalConditionsComponent } from "./edit-additional-conditions/edit-additional-conditions.component";
import { EditAdminConditionsComponent } from "./edit-admin-conditions/edit-admin-conditions.component";
import { EditEnvironmentConditionsComponent } from "./edit-environment-conditions/edit-environment-conditions.component";
import { EditUserConditionsComponent } from "./edit-user-conditions/edit-user-conditions.component";

@Component({
  selector: "app-edit-conditions-tab",
  standalone: true,
  imports: [
    EditAdminConditionsComponent,
    EditUserConditionsComponent,
    EditEnvironmentConditionsComponent,
    EditAdditionalConditionsComponent
  ],
  templateUrl: "./edit-conditions-tab.component.html",
  styleUrl: "./edit-conditions-tab.component.scss"
})
export class EditConditionsTabComponent {
  policyService: PolicyServiceInterface = inject(PolicyService);

  policy = input.required<PolicyDetail>();
  policyEdit = output<Partial<PolicyDetail>>();

  onPolicyEdit($event: Partial<PolicyDetail>) {
    this.policyEdit.emit($event);
  }
}
