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

import { Component, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatIconModule } from "@angular/material/icon";
import {
  PolicyServiceInterface as PolicyServiceInterface,
  PolicyService as PolicyService
} from "../../../../../services/policies/policies.service";
import { SelectorButtons } from "../selector-buttons/selector-buttons.component";

import { MatTooltipModule } from "@angular/material/tooltip";

@Component({
  selector: "app-action-selector",
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, SelectorButtons, MatTooltipModule],
  templateUrl: "./action-selector.component.html",
  styleUrls: ["./action-selector.component.scss"]
})
export class ActionSelectorComponent {
  policyService: PolicyServiceInterface = inject(PolicyService);
  testngModelChange(event: string) {
    this.policyService.actionFilter.set(event);
    throw Error(event);
  }
}
