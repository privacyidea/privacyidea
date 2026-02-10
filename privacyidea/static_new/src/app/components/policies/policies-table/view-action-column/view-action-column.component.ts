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

import { Component, computed, inject, input } from "@angular/core";
import { PolicyService, PolicyServiceInterface } from "../../../../services/policies/policies.service";

@Component({
  selector: "app-view-action-column",
  standalone: true,
  templateUrl: "./view-action-column.component.html",
  styleUrl: "./view-action-column.component.scss"
})
export class ViewActionColumnComponent {
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);

  /**
   * Input received from the policy table row.
   */
  readonly actions = input.required<{ [actionName: string]: any }>();

  /**
   * Pre-calculates the display list including the boolean check
   * to avoid expensive template function calls.
   */
  readonly actionsList = computed(() =>
    Object.entries(this.actions()).map(([name, value]) => ({
      name,
      value,
      isBoolean: this.policyService.getDetailsOfAction(name)?.type === "bool"
    }))
  );
}
