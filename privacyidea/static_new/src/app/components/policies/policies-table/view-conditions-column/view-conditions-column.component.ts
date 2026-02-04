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

import { Component, input, computed } from "@angular/core";
import {
  AdditionalCondition,
  COMPARATOR_OPTIONS,
  ComparatorOptionKey,
  HANDLE_MISSING_DATA_OPTIONS,
  HandleMissingDataOptionKey,
  PolicyDetail,
  SECTION_OPTIONS,
  SectionOptionKey
} from "../../../../services/policies/policies.service";
import { ViewConditionSectionComponent } from "./view-condition-section/view-condition-section.component";
import { MatIconModule } from "@angular/material/icon";

@Component({
  selector: "app-view-conditions-column",
  standalone: true,
  imports: [MatIconModule, ViewConditionSectionComponent],
  templateUrl: "./view-conditions-column.component.html",
  styleUrl: "./view-conditions-column.component.scss"
})
export class ConditionsTabComponent {
  policy = input.required<PolicyDetail>();

  // Admin Conditions
  selectedAdmins = computed(() => this.policy().adminuser || []);
  selectedAdminrealm = computed(() => this.policy().adminrealm || []);

  // User Conditions
  selectedRealms = computed(() => this.policy().realm || []);
  selectedResolvers = computed(() => this.policy().resolver || []);
  selectedUsers = computed(() => this.policy().user || []);
  userCaseInsensitive = computed(() => this.policy().user_case_insensitive || false);

  // Environment Conditions
  selectedPinodes = computed<string[]>(() => this.policy().pinode || []);
  selectedValidTime = computed(() => this.policy().time || "");
  selectedClient = computed(() => this.policy().client || []);
  selectedUserAgents = computed(() => this.policy().user_agents || []);

  // Additional Conditions
  additionalConditions = computed<AdditionalCondition[]>(() => this.policy().conditions || []);
  getSectionLabel(key: SectionOptionKey): string {
    return SECTION_OPTIONS.find((o) => o.key === key)?.label ?? key;
  }
  getComparatorLabel(key: ComparatorOptionKey): string {
    return COMPARATOR_OPTIONS.find((o) => o.key === key)?.label ?? key;
  }
  getMissingDataLabel(key: HandleMissingDataOptionKey): string {
    return HANDLE_MISSING_DATA_OPTIONS.find((o) => o.key === key)?.label ?? key;
  }
}
