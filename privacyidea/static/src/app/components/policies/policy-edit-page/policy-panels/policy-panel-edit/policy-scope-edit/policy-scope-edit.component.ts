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

import { Component, inject, input, output } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule } from "@angular/material/select";
import { MatTooltipModule } from "@angular/material/tooltip";
import { PolicyService, PolicyServiceInterface } from "@services/policies/policies.service";

@Component({
  selector: "app-policy-scope-edit",
  templateUrl: "./policy-scope-edit.component.html",
  styleUrl: "./policy-scope-edit.component.scss",
  standalone: true,
  imports: [MatFormFieldModule, MatSelectModule, MatTooltipModule]
})
export class PolicyScopeEditComponent {
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);

  readonly scope = input.required<string>();
  readonly disabled = input<boolean>(false);
  readonly scopeChange = output<string>();

  readonly allPolicyScopes = this.policyService.allPolicyScopes;

  readonly lockedHint = $localize`:@@policy.scopeLockedHint:Remove all actions of this policy to change its scope.`;
}
