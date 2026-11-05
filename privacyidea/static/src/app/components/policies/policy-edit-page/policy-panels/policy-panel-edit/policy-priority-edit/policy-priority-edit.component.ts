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
import { Component, computed, model } from "@angular/core";
import { form, FormField, min, required } from "@angular/forms/signals";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { ERR } from "@utils/form-rules.utils";
import { hasError } from "@utils/form-state.utils";

/** The lowest priority the backend accepts (`set_policy` rejects priorities below 1). */
export const MIN_POLICY_PRIORITY = 1;

@Component({
  selector: "app-policy-priority-edit",
  templateUrl: "./policy-priority-edit.component.html",
  styleUrl: "./policy-priority-edit.component.scss",
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, FormField, TextFieldModule]
})
export class PolicyPriorityEditComponent {
  /** `null` while the field is empty. */
  readonly priority = model.required<number | null>();
  readonly priorityField = form(this.priority, (f) => {
    required(f);
    min(f, MIN_POLICY_PRIORITY);
  });

  /** True while the priority is a number of at least 1. */
  readonly valid = computed(() => this.priorityField().valid());

  protected readonly ERR = ERR;
  protected readonly hasError = hasError;
}
