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
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { FormsModule } from "@angular/forms";
import { TextFieldModule } from "@angular/cdk/text-field";
import { PolicyDetail, PolicyService } from "../../../../../services/policies/policies.service";
import { DocumentationService } from "../../../../../services/documentation/documentation.service";

@Component({
  selector: "app-policy-description",
  templateUrl: "./policy-description.component.html",
  styleUrls: ["./policy-description.component.scss"],
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, FormsModule, TextFieldModule]
})
export class PolicyDescriptionComponent {
  // Services
  documentationService = inject(DocumentationService);

  // Component State
  isEditMode = input.required<boolean>();
  policy = input.required<PolicyDetail>();
  policyChange = output<PolicyDetail>();

  openDocumentation(page: string) {
    this.documentationService.openDocumentation(page);
  }

  updatePolicyDescription($event: string) {
    this.updateSelectedPolicy({ description: $event });
  }
  updateSelectedPolicy(patch: Partial<PolicyDetail>) {
    this.policyChange.emit({ ...this.policy(), ...patch });
  }
}
