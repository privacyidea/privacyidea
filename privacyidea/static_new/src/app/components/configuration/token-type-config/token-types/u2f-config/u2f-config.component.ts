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
import { Component, computed, input, output } from "@angular/core";

import { MatExpansionModule } from "@angular/material/expansion";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { U2F_APP_ID } from "@constants/token.constants";

@Component({
  selector: "app-u2f-config",
  standalone: true,
  imports: [MatExpansionModule, MatFormFieldModule, MatInputModule],
  templateUrl: "./u2f-config.component.html",
  styleUrl: "./u2f-config.component.scss"
})
export class U2fConfigComponent {
  protected readonly U2F_APP_ID = U2F_APP_ID;

  formData = input.required<Record<string, string | undefined>>();
  formDataChange = output<Record<string, string | undefined>>();

  appId = computed(() => this.formData()[U2F_APP_ID] ?? "");

  updateFormData(fieldName: string, value: string): void {
    const newValue = { ...this.formData(), [fieldName]: value };
    this.formDataChange.emit(newValue);
  }
}
