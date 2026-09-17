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

import { TextFieldModule } from "@angular/cdk/text-field";
import { Component, model } from "@angular/core";
import { form, FormField, pattern, required } from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-policy-name-edit",
  templateUrl: "./policy-name-edit.component.html",
  styleUrl: "./policy-name-edit.component.scss",
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, FormField, TextFieldModule, ClearableInputComponent]
})
export class PolicyNameEditComponent {
  readonly policyName = model.required<string>();
  readonly nameField = form(this.policyName, (f) => {
    required(f);
    pattern(f, /^[a-zA-Z0-9._-]*$/);
  });
}
