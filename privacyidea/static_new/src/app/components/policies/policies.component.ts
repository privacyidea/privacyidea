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

import { Component, inject, signal } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";
import { PolicyService, PolicyServiceInterface } from "../../services/policies/policies.service";
import { MatIconModule } from "@angular/material/icon";
import { AuthService, AuthServiceInterface } from "../../services/auth/auth.service";
import { FilterValue } from "../../core/models/filter_value";
import { PolicyFilterComponent } from "./policy-panels/policy-filter/policy-filter.component";
import { PolicyPanelComponent } from "./policy-panels/policy-panel/policy-panel.component";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [CommonModule, MatExpansionModule, MatIconModule, PolicyFilterComponent, PolicyPanelComponent],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss"
})
export class PoliciesComponent {
  readonly policyService: PolicyServiceInterface = inject(PolicyService);
  readonly authService: AuthServiceInterface = inject(AuthService);

  allPoliciesList = this.policyService.allPolicies;

  currentFilter = signal<FilterValue>(new FilterValue());
}
