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
import { CommonModule } from "@angular/common";
import { PolicyDetail } from "../../../../../../services/policies/policies.service";
import { ReadonlyChipSectionComponent } from "../readonly-chip-section/readonly-chip-section.component";

@Component({
  selector: "app-conditions-environment-view",
  standalone: true,
  imports: [
    CommonModule,
    ReadonlyChipSectionComponent
  ],
  templateUrl: "./conditions-environment-view.component.html",
  styleUrl: "./conditions-environment-view.component.scss" // Assuming a new SCSS file for view
})
export class ConditionsEnvironmentViewComponent {
  policy = input.required<PolicyDetail>();

  selectedPinodes = computed<string[]>(() => this.policy().pinode || []);
  selectedValidTime = computed(() => this.policy().time || "");
  selectedClient = computed(() => this.policy().client || []);
  selectedUserAgents = computed(() => this.policy().user_agents || []);
}
